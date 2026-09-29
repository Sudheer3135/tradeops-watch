# Phase 2 incident: slow-feed

This was a deliberate lab drill on 2026-09-29, not a production incident.

## Impact and cause

Injected cause: 350 ms delay on price responses. The selected live alert was **HighOrderLatency (P2)**.
Prometheus and Alertmanager both contained it during the fault. Grafana's
provisioned dashboard and live alert query succeeded, and its Loki proxy returned
real log streams. The saved WARN/ERROR search contains 8 lines (at most 1000);
this count can include other operational messages within the displayed window.
Use the raw labels and messages to attribute individual symptoms.

## UTC timeline

| Event | Timestamp |
|---|---|
| Fault command started | 2026-09-29T16:59:25.780550Z |
| Prometheus activeAt (condition became active, possibly pending) | 2026-09-29T16:59:48.889371656Z |
| Alertmanager startsAt | 2026-09-29T17:01:48.889Z |
| First observed firing in both APIs | 2026-09-29T17:01:53.066472Z |
| Runbook fix started | 2026-09-29T17:01:54.325808Z |
| Selected alert absent from both APIs | 2026-09-29T17:02:54.966701Z |
| Original Bash health check returned zero | 2026-09-29T17:02:56.093191Z |
| Cleanup completed | 2026-09-29T17:02:56.131212Z |

The verifier polls every five seconds plus request time, so observations are not
exact transition times. API `activeAt` is not presented as the first firing time.
For a restart drill, a P3 naturally persists for ten minutes after recovery.
Other drills can also create expected recent-start alerts; “resolved” above
refers to the selected alert, not a claim that every unrelated alert vanished.

## Investigation, repair and verification

Followed [the port-blocked runbook](../runbooks/port-blocked.md): correlate the alert
with Trading / p50, p95 and p99 latency, inspect logs, use the fault-specific undo command, then recheck
alert APIs and the original Bash monitor. Exact commands, exit statuses and
health values are in the terminal record. The CPU drill additionally has a
120-second automatic stop; the record shows when the manual fix was issued.
No error logs or metric history were cleared to make recovery pass.

## Evidence

- [Timeline and matching alert labels](../docs/evidence/phase2/slow-feed/timeline.json)
- [Terminal commands and health checks](../docs/evidence/phase2/slow-feed/terminal.txt)
- [Prometheus firing](../docs/evidence/phase2/slow-feed/prometheus-firing.json)
- [Alertmanager firing](../docs/evidence/phase2/slow-feed/alertmanager-firing.json)
- [Prometheus after recovery](../docs/evidence/phase2/slow-feed/prometheus-resolved.json)
- [Alertmanager after recovery](../docs/evidence/phase2/slow-feed/alertmanager-resolved.json)
- [Grafana alert query](../docs/evidence/phase2/slow-feed/grafana-firing-alerts.json)
- [Grafana Loki query](../docs/evidence/phase2/slow-feed/grafana-loki-logs.json)
- [WARN/ERROR history](../docs/evidence/phase2/slow-feed/loki-errors-warnings.json)
- [Alert state history](../docs/evidence/phase2/slow-feed/alert-history.json)

## Follow-up

Keep the recovery command next to the injection command, establish a healthy
baseline before repeating, and preserve timestamps before making changes.
Capture manual screenshots using the [exact window](../docs/screenshots/README.md).
This drill validates a small VM; it establishes no production availability SLO.
