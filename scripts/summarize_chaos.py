#!/usr/bin/env python3
"""Build reports only from completed real runs, preserving raw evidence separately."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs/evidence/phase2"
DETAILS = {
    "fill-disk": (
        "disk-full",
        "Root filesystem pressure",
        "System / root disk usage",
        "DiskAlmostFull",
    ),
    "cpu-spike": ("high-cpu", "Bounded CPU saturation", "System / CPU and load", "HighCPU"),
    "slow-feed": (
        "port-blocked",
        "350 ms delay on price responses",
        "Trading / p50, p95 and p99 latency",
        "HighOrderLatency",
    ),
    "kill-feed": (
        "service-down",
        "Feed process killed; systemd automatically restarts it",
        "Service health / process age and restarts",
        "ServiceRestartedRecently",
    ),
    "stop-feed": (
        "service-down",
        "Feed service deliberately stopped",
        "Service health / scrape and probe status",
        "ServiceDown",
    ),
    "block-port": (
        "port-blocked",
        "Tagged firewall rule rejects loopback TCP 9001",
        "Service health / probe failures",
        "HealthProbeFailed",
    ),
    "net-delay": (
        "port-blocked",
        "500 ms netem delay on loopback",
        "Service health and Trading / failures and latency",
        "HealthProbeFailed",
    ),
}


def parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def query_json(url, destination):
    with urlopen(url, timeout=30) as response:
        result = json.load(response)
    assert result["status"] == "success", result
    destination.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    index = [
        "# Phase 2 real chaos evidence",
        "",
        "These are actual fault runs in the isolated Ubuntu VM. API snapshots are",
        "captured with curl; Grafana and Loki were also queried while the alert fired.",
        "No screenshots, Telegram delivery or production incident claims are implied.",
        "",
        "| Scenario | Fault start (UTC) | Firing observed | Selected alert cleared | Bash healthy |",
        "|---|---|---|---|---|",
    ]
    shots = [
        "# Manual screenshot checklist",
        "",
        "No screenshots have been taken. Use UTC in Grafana. Current VM URL:",
        "http://192.168.2.2:3000/d/tradeops-overview (check `multipass info tradeops`).",
        "Save images in this folder with the filenames below. History is retained for",
        "about two days; if expired, rerun a controlled drill and record the new times.",
        "",
        "## Historical metrics and logs from the actual runs",
        "",
        "For each metrics image, open the linked dashboard and expand the named row.",
        "For the logs image, open Grafana Explore, choose Loki, use",
        '`{job="tradeops",level=~"ERROR|WARN"}` and set the identical absolute UTC window.',
        "An empty error result is valid for a fault that did not cause application errors;",
        'then use `{job="tradeops"}` to show continuity, and state what is visible.',
        "",
        "| Metrics filename / dashboard | UTC From → To | Panel / expected evidence | Logs filename |",
        "|---|---|---|---|",
    ]
    fault_starts = [
        parse(json.loads(path.read_text())["fault_started_at"])
        for path in EVIDENCE.glob("*/timeline.json")
        if "fault_started_at" in json.loads(path.read_text())
    ]
    for scenario, (runbook, cause, panels, alert) in DETAILS.items():
        folder = EVIDENCE / scenario
        path = folder / "timeline.json"
        if not path.exists():
            continue
        timeline = json.loads(path.read_text())
        if timeline["status"] != "passed":
            index.append(
                f"| {scenario} — FAILED, see timeline | {timeline.get('fault_started_at', 'not injected')} | — | — | — |"
            )
            continue
        start = parse(timeline["fault_started_at"]) - timedelta(minutes=1)
        end = parse(timeline["healthy_at"]) + timedelta(minutes=1)
        # The extra minute is a display margin, cut short before the next drill's fault
        # so a window never shows another scenario; no future observations are invented.
        later = [f for f in fault_starts if f > parse(timeline["fault_started_at"])]
        if later:
            end = min(end, min(later) - timedelta(seconds=1))
        params = {
            "query": f'ALERTS{{alertname="{alert}"}}',
            "start": start.timestamp(),
            "end": min(end.timestamp(), datetime.now(timezone.utc).timestamp()),
            "step": "15",
        }
        query_json(
            "http://127.0.0.1:9090/api/v1/query_range?" + urlencode(params),
            folder / "alert-history.json",
        )
        log_params = {
            "query": '{job="tradeops",level=~"ERROR|WARN"}',
            "start": str(int(start.timestamp() * 10**9)),
            "end": str(int(min(end.timestamp(), datetime.now(timezone.utc).timestamp()) * 10**9)),
            "limit": 1000,
            "direction": "forward",
        }
        logs = query_json(
            "http://127.0.0.1:3100/loki/api/v1/query_range?" + urlencode(log_params),
            folder / "loki-errors-warnings.json",
        )
        lines = sum(len(stream["values"]) for stream in logs["data"]["result"])
        firing = timeline["firing"]
        active = sorted({a["activeAt"] for a in firing["prometheus"]})
        received = sorted({a["startsAt"] for a in firing["alertmanager"]})
        severities = sorted({a["labels"]["severity"] for a in firing["prometheus"]})
        day = parse(timeline["fault_started_at"]).date()
        name = f"phase2-{day:%Y%m%d}-{scenario}"
        inhibition = ""
        if (folder / "inhibition.json").exists():
            proof = json.loads((folder / "inhibition.json").read_text())
            muted = ", ".join(
                f"{a['labels']['alertname']}/{a['labels']['service']} ({a['labels']['instance']})"
                for a in proof["inhibited_same_service"]
            )
            other = ", ".join(
                f"{a['labels']['alertname']}/{a['labels']['service']}"
                for a in proof["active_other_service"]
            )
            inhibition = f"""
## Inhibition observed during this fault

At {proof["observed_at"]} Alertmanager held ServiceDown/feed active and marked
{muted} as `suppressed`, with `inhibitedBy` set to the ServiceDown fingerprint.
{other} stayed `active` because it belongs to a different service. Prometheus
still evaluated every rule; inhibition only mutes notifications.
[Raw Alertmanager records](../docs/evidence/phase2/{scenario}/inhibition.json).
"""
        report = f"""# Phase 2 incident: {scenario}

This was a deliberate lab drill on {day}, not a production incident.

## Impact and cause

Injected cause: {cause}. The selected live alert was **{alert} ({", ".join(severities)})**.
Prometheus and Alertmanager both contained it during the fault. Grafana's
provisioned dashboard and live alert query succeeded, and its Loki proxy returned
real log streams. The saved WARN/ERROR search contains {lines} lines (at most 1000);
this count can include other operational messages within the displayed window.
Use the raw labels and messages to attribute individual symptoms.

## UTC timeline

| Event | Timestamp |
|---|---|
| Fault command started | {timeline["fault_started_at"]} |
| Prometheus activeAt (condition became active, possibly pending) | {", ".join(active)} |
| Alertmanager startsAt | {", ".join(received)} |
| First observed firing in both APIs | {firing["observed_at"]} |
| Runbook fix started | {timeline["fix_started_at"]} |
| Selected alert absent from both APIs | {timeline["resolved"]["observed_at"]} |
| Original Bash health check returned zero | {timeline["healthy_at"]} |
| Cleanup completed | {timeline["finished_at"]} |

The verifier polls every five seconds plus request time, so observations are not
exact transition times. API `activeAt` is not presented as the first firing time.
For a restart drill, a P3 naturally persists for ten minutes after recovery.
Other drills can also create expected recent-start alerts; “resolved” above
refers to the selected alert, not a claim that every unrelated alert vanished.

## Investigation, repair and verification

Followed [the {runbook} runbook](../runbooks/{runbook}.md): correlate the alert
with {panels}, inspect logs, use the fault-specific undo command, then recheck
alert APIs and the original Bash monitor. Exact commands, exit statuses and
health values are in the terminal record. The CPU drill additionally has a
120-second automatic stop; the record shows when the manual fix was issued.
No error logs or metric history were cleared to make recovery pass.
{inhibition}
## Evidence

- [Timeline and matching alert labels](../docs/evidence/phase2/{scenario}/timeline.json)
- [Terminal commands and health checks](../docs/evidence/phase2/{scenario}/terminal.txt)
- [Prometheus firing](../docs/evidence/phase2/{scenario}/prometheus-firing.json)
- [Alertmanager firing](../docs/evidence/phase2/{scenario}/alertmanager-firing.json)
- [Prometheus after recovery](../docs/evidence/phase2/{scenario}/prometheus-resolved.json)
- [Alertmanager after recovery](../docs/evidence/phase2/{scenario}/alertmanager-resolved.json)
- [Grafana alert query](../docs/evidence/phase2/{scenario}/grafana-firing-alerts.json)
- [Grafana Loki query](../docs/evidence/phase2/{scenario}/grafana-loki-logs.json)
- [WARN/ERROR history](../docs/evidence/phase2/{scenario}/loki-errors-warnings.json)
- [Alert state history](../docs/evidence/phase2/{scenario}/alert-history.json)

## Follow-up

Keep the recovery command next to the injection command, establish a healthy
baseline before repeating, and preserve timestamps before making changes.
Capture manual screenshots using the [exact window](../docs/screenshots/README.md).
This drill validates a small VM; it establishes no production availability SLO.
"""
        (ROOT / "incidents" / f"{name}.md").write_text(report)
        index.append(
            f"| [{scenario}](../../../incidents/{name}.md) | {timeline['fault_started_at']} | {firing['observed_at']} | {timeline['resolved']['observed_at']} | {timeline['healthy_at']} |"
        )
        url = "http://192.168.2.2:3000/d/tradeops-overview?" + urlencode(
            {
                "from": int(start.timestamp() * 1000),
                "to": int(end.timestamp() * 1000),
                "timezone": "utc",
            }
        )
        shots.append(
            f"| [phase2-{scenario}-metrics.png]({url}) | {stamp(start)} → {stamp(end)} | {panels}; fault and recovery | `phase2-{scenario}-logs.png` |"
        )
    for aborted in sorted(EVIDENCE.glob("*-aborted-*/timeline.json")):
        timeline = json.loads(aborted.read_text())
        index.append(
            f"| {aborted.parent.name} — ABORTED ({timeline['error']}); rerun above | "
            f"{timeline['fault_started_at']} | — | — | — |"
        )
    index += [
        "",
        "Each scenario directory contains baseline, firing, resolved and final healthy",
        "API snapshots plus Grafana/Loki responses. `timeline.json` is the source for",
        "the incident report. `poll` files are only the latest polling sample.",
        "",
        "`step8-ci.txt` records the local CI run; synthetic Prometheus rule fixtures",
        "are unit tests, not these real faults. Earlier step evidence remains intact.",
    ]
    shots += [
        "",
        "## Additional screenshots",
        "",
        "- `phase2-overview-healthy.png`: dashboard, Last 15 minutes after final recovery, all five rows; service/probes up and active alerts empty (or explain a recent-start P3).",
        '- `phase2-slow-feed-trading.png`: the slow-feed UTC window above, Trading row; elevated p95 followed by recovery. Logs of successful slow orders use `{job="tradeops",service="orders"} |= "latency_ms="`.',
        "- `phase2-stop-feed-alerts.png`: http://192.168.2.2:9090/alerts during a fresh stop-feed drill, once ServiceDown is firing. This page shows current alerts, not historical snapshots.",
        "- `phase2-stop-feed-alertmanager.png`: http://192.168.2.2:9093 during that same fresh drill; show grouped alert labels and inhibition. Save the new UTC time beside the screenshot, then fix-feed and verify recovery.",
        '- `phase2-stop-feed-logs.png`: Loki Explore with the stop-feed window above and `{job="tradeops",service="orders"} |= "feed unreachable"`; show actual dependency errors.',
        '- `phase2-alert-history.png`: Grafana Explore / Prometheus, range query `ALERTS{alertname="HighOrderLatency",alertstate="firing"}` over the slow-feed window; show the firing interval. Active-alert tables cannot reconstruct resolved incidents.',
        "- `phase2-deploy-rollback.png`: terminal displaying `docs/evidence/phase2/step7-deploy-rollback.txt`; include failed health gate, automatic restore and subsequent successful health result with UTC timestamps.",
        "- `phase2-ci-success.png`: your repository's Actions page only after an actual hosted run passes. Include commit hash and green result; local CI output is not a hosted run.",
        "",
        "Do not expose `.env`, bot tokens, passwords or chat IDs in screenshots.",
    ]
    taken = ROOT / "docs/screenshots/taken.json"
    if taken.exists():
        shots[2] = "Screenshots were captured with headless Chromium (times below). VM URL:"
        shots += [
            "",
            "## Screenshots taken (UTC)",
            "",
            "| File | Taken at | Note |",
            "|---|---|---|",
        ]
        shots += [
            f"| [{row['file']}]({row['file']}) | {row['taken_at']} | {row['note']} |"
            for row in json.loads(taken.read_text())
        ]
    (EVIDENCE / "README.md").write_text("\n".join(index) + "\n")
    (ROOT / "docs/screenshots").mkdir(exist_ok=True)
    (ROOT / "docs/screenshots/README.md").write_text("\n".join(shots) + "\n")


if __name__ == "__main__":
    main()
