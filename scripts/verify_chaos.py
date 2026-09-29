#!/usr/bin/env python3
"""Run real VM faults sequentially and preserve API evidence; never synthesize alerts."""

import argparse
import base64
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CHAOS = "/opt/tradeops/scripts/chaos.sh"
SCENARIOS = {
    "kill-feed": ("fix-feed", "ServiceRestartedRecently", "feed"),
    "stop-feed": ("fix-feed", "ServiceDown", "feed"),
    "fill-disk": ("fix-disk", "DiskAlmostFull", "host"),
    "cpu-spike": ("fix-cpu", "HighCPU", "host"),
    "block-port": ("fix-port", "HealthProbeFailed", "feed"),
    "net-delay": ("fix-delay", "HealthProbeFailed", None),
    "slow-feed": ("fix-slow-feed", "HighOrderLatency", "orders"),
}


RUN_LOG = ROOT / "docs/evidence/phase2/step9-chaos-run.txt"


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(*parts):
    """Append progress to the evidence log; a closed terminal must not abort a live fault."""
    line = " ".join(str(part) for part in (utc(), *parts))
    with RUN_LOG.open("a") as output:
        output.write(line + "\n")
    try:
        print(line, flush=True)
    except OSError:
        pass


def fetch(url, auth=None):
    headers = {"Authorization": auth} if auth else {}
    with urlopen(Request(url, headers=headers), timeout=40) as response:
        return json.load(response)


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def matches(alert, name, service):
    labels = alert["labels"]
    return labels.get("alertname") == name and (service is None or labels.get("service") == service)


def snapshot(folder, stage):
    prom = json.loads(
        subprocess.check_output(
            ["curl", "-fsS", "--max-time", "40", "http://127.0.0.1:9090/api/v1/alerts"], text=True
        )
    )
    am = json.loads(
        subprocess.check_output(
            ["curl", "-fsS", "--max-time", "40", "http://127.0.0.1:9093/api/v2/alerts"], text=True
        )
    )
    save(folder / f"prometheus-{stage}.json", prom)
    save(folder / f"alertmanager-{stage}.json", am)
    return prom["data"]["alerts"], am


def describe(alerts):
    return ", ".join(
        f"{a['labels'].get('alertname')}/{a['labels'].get('service')}/"
        f"{a.get('state') or a.get('status', {}).get('state')}"
        for a in alerts
    )


def wait_alert(folder, name, service, firing, timeout, stage):
    """Firing needs the alert firing in both APIs; clear needs it absent in every state."""
    deadline = time.monotonic() + timeout
    blocking = []
    while time.monotonic() < deadline:
        try:
            prom, am = snapshot(folder, "poll")
            p = [a for a in prom if matches(a, name, service)]
            a = [a for a in am if matches(a, name, service)]
            if firing:
                p = [x for x in p if x["state"] == "firing"]
            if (p and a) if firing else (not p and not a):
                snapshot(folder, stage)
                return {"observed_at": utc(), "prometheus": p, "alertmanager": a}
            blocking = p + a
        except (OSError, ValueError) as error:
            log("API retry", error)
        time.sleep(5)
    wanted = "firing in Prometheus and Alertmanager" if firing else "absent from both APIs"
    raise TimeoutError(
        f"{name} (service={service}) was not {wanted} within {timeout}s; "
        f"last matching alerts: {describe(blocking) or 'none'}"
    )


def wait_process_age(service, minimum, timeout):
    query = urlencode(
        {"query": f'time()-process_start_time_seconds{{job="tradeops",service="{service}"}}'}
    )
    deadline = time.monotonic() + timeout
    age = None
    while time.monotonic() < deadline:
        result = fetch("http://127.0.0.1:9090/api/v1/query?" + query)["data"]["result"]
        age = float(result[0]["value"][1]) if result else None
        if age is not None and age >= minimum:
            return
        time.sleep(15)
    raise TimeoutError(
        f"{service} process age was {age} (None means not scraped); needed >= {minimum}s "
        f"within {timeout}s. Check that the service is running."
    )


def wait_inhibition(folder, timeout):
    """Real stop-feed proof: ServiceDown mutes same-service alerts, not other services."""
    deadline = time.monotonic() + timeout
    am = []
    while time.monotonic() < deadline:
        try:
            am = fetch("http://127.0.0.1:9093/api/v2/alerts")
        except (OSError, ValueError) as error:
            log("API retry", error)
            time.sleep(5)
            continue
        source = [a for a in am if matches(a, "ServiceDown", "feed")]
        muted = [
            a
            for a in am
            if matches(a, "HealthProbeFailed", "feed")
            and a["status"]["state"] == "suppressed"
            and set(a["status"]["inhibitedBy"]) & {s["fingerprint"] for s in source}
        ]
        other = [
            a
            for a in am
            if matches(a, "FeedErrorsHigh", "orders")
            and a["status"]["state"] == "active"
            and not a["status"]["inhibitedBy"]
        ]
        if source and muted and other:
            result = {
                "observed_at": utc(),
                "rule": "ServiceDown P1 inhibits same service/environment symptoms",
                "source": source,
                "inhibited_same_service": muted,
                "active_other_service": other,
            }
            save(folder / "inhibition.json", result)
            return result
        time.sleep(5)
    raise TimeoutError(
        f"Inhibition not observed within {timeout}s; Alertmanager had: {describe(am) or 'none'}"
    )


def observe(folder, auth, start):
    base = "http://127.0.0.1:3000"
    dashboard = fetch(base + "/api/dashboards/uid/tradeops-overview", auth)
    assert dashboard["meta"]["provisioned"]
    save(folder / "grafana-dashboard.json", dashboard)
    query = urlencode({"query": 'ALERTS{alertstate="firing"}'})
    alerts = fetch(base + "/api/datasources/proxy/uid/prometheus/api/v1/query?" + query, auth)
    assert alerts["status"] == "success" and alerts["data"]["result"]
    save(folder / "grafana-firing-alerts.json", alerts)
    query = urlencode(
        {
            "query": '{job="tradeops"}',
            "start": str(start),
            "end": str(time.time_ns()),
            "limit": 100,
            "direction": "backward",
        }
    )
    logs = fetch(base + "/api/datasources/proxy/uid/loki/loki/api/v1/query_range?" + query, auth)
    assert logs["status"] == "success" and logs["data"]["result"]
    save(folder / "grafana-loki-logs.json", logs)
    save(folder / "loki-logs.json", fetch("http://127.0.0.1:3100/loki/api/v1/query_range?" + query))


def command(args, log):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with log.open("a") as output:
        output.write(f"{utc()} $ {' '.join(args)}\n{result.stdout}exit={result.returncode}\n")
    return result


def main():
    if platform.system() != "Linux" or platform.node() != "tradeops":
        raise SystemExit("Run only inside the tradeops VM")
    parser = argparse.ArgumentParser()
    parser.add_argument("scenarios", nargs="*", choices=list(SCENARIOS))
    args = parser.parse_args()
    password = next(
        line.split("=", 1)[1]
        for line in (ROOT / "monitoring/.env").read_text().splitlines()
        if line.startswith("GRAFANA_ADMIN_PASSWORD=")
    )
    auth = "Basic " + base64.b64encode(("admin:" + password).encode()).decode()
    for scenario in args.scenarios or SCENARIOS:
        folder = ROOT / "docs/evidence/phase2" / scenario
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / "timeline.json").exists():
            raise SystemExit(f"Refusing to overwrite existing run: {folder}")
        fix, name, service = SCENARIOS[scenario]
        timeline = {
            "scenario": scenario,
            "expected_alert": name,
            "service": service,
            "baseline_started_at": utc(),
        }
        terminal = folder / "terminal.txt"
        try:
            log(scenario, "waiting for clean alert baseline")
            if scenario == "kill-feed":
                # A new restart is only provable once the previous recent-start P3 has expired.
                wait_process_age("feed", 610, 900)
            wait_alert(folder, name, service, False, 900, "baseline")
            timeline["fault_started_at"] = utc()
            start = time.time_ns() - 60 * 10**9
            result = command(["sudo", CHAOS, scenario], terminal)
            result.check_returncode()
            log(scenario, "fault injected")
            timeline["firing"] = wait_alert(folder, name, service, True, 480, "firing")
            log(scenario, "confirmed in Prometheus and Alertmanager")
            if scenario == "stop-feed":
                timeline["inhibition"] = wait_inhibition(folder, 240)["observed_at"]
                log(scenario, "inhibition confirmed: feed probe muted, orders errors active")
            observe(folder, auth, start)
            command(["sudo", "/opt/tradeops/scripts/healthcheck.sh"], terminal)
            timeline["fix_started_at"] = utc()
            command(["sudo", CHAOS, fix], terminal).check_returncode()
            timeline["resolved"] = wait_alert(folder, name, service, False, 900, "resolved")
            deadline = time.monotonic() + 420
            while True:
                result = command(["sudo", "/opt/tradeops/scripts/healthcheck.sh"], terminal)
                if result.returncode == 0:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Phase 1 healthcheck did not return to healthy in 420s")
                time.sleep(15)
            timeline["healthy_at"] = utc()
            timeline["status"] = "passed"
            snapshot(folder, "healthy")
            log(scenario, "PASS resolved and Phase 1 healthy")
        except Exception as error:
            timeline["status"] = "failed"
            timeline["error"] = repr(error)
            log(scenario, "FAILED", repr(error))
            raise
        finally:
            command(["sudo", CHAOS, "cleanup"], terminal)
            timeline["finished_at"] = utc()
            save(folder / "timeline.json", timeline)


if __name__ == "__main__":
    main()
