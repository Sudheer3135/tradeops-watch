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


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def wait_alert(folder, name, service, firing, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            prom, am = snapshot(folder, "poll")
            p = [a for a in prom if matches(a, name, service) and a["state"] == "firing"]
            a = [a for a in am if matches(a, name, service)]
            if (p and a) if firing else (not p and not a):
                stage = "firing" if firing else "resolved"
                snapshot(folder, stage)
                return {"observed_at": utc(), "prometheus": p, "alertmanager": a}
        except (OSError, ValueError) as error:
            print(utc(), "API retry", str(error), flush=True)
        time.sleep(5)
    raise TimeoutError(f"{name} firing={firing} did not converge in {timeout}s")


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
        log = folder / "terminal.txt"
        try:
            print(utc(), scenario, "waiting for clean alert baseline", flush=True)
            if scenario == "kill-feed":
                while True:
                    age = fetch("http://127.0.0.1:9090/api/v1/query?" + urlencode({"query": 'time()-process_start_time_seconds{job="tradeops",service="feed"}'}))["data"]["result"]
                    if age and float(age[0]["value"][1]) >= 610:
                        break
                    time.sleep(15)
            wait_alert(folder, name, service, False, 900)
            snapshot(folder, "baseline")
            timeline["fault_started_at"] = utc()
            start = time.time_ns() - 60 * 10**9
            result = command(["sudo", CHAOS, scenario], log)
            result.check_returncode()
            print(utc(), scenario, "fault injected", flush=True)
            timeline["firing"] = wait_alert(folder, name, service, True, 480)
            print(utc(), scenario, "confirmed in Prometheus and Alertmanager", flush=True)
            observe(folder, auth, start)
            command(["sudo", "/opt/tradeops/scripts/healthcheck.sh"], log)
            timeline["fix_started_at"] = utc()
            command(["sudo", CHAOS, fix], log).check_returncode()
            timeline["resolved"] = wait_alert(folder, name, service, False, 900)
            deadline = time.monotonic() + 420
            while True:
                result = command(["sudo", "/opt/tradeops/scripts/healthcheck.sh"], log)
                if result.returncode == 0:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Phase 1 healthcheck did not return to healthy")
                time.sleep(15)
            timeline["healthy_at"] = utc()
            timeline["status"] = "passed"
            snapshot(folder, "healthy")
            print(utc(), scenario, "PASS resolved and Phase 1 healthy", flush=True)
        except Exception as error:
            timeline["status"] = "failed"
            timeline["error"] = repr(error)
            raise
        finally:
            command(["sudo", CHAOS, "cleanup"], log)
            timeline["finished_at"] = utc()
            save(folder / "timeline.json", timeline)


if __name__ == "__main__":
    main()
