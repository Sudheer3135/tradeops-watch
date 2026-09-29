# Phase 2 incident: stop-feed

This was a deliberate lab drill on 2026-09-29, not a production incident.

## Impact and cause

Injected cause: Feed service deliberately stopped. The selected live alert was **ServiceDown (P1)**.
Prometheus and Alertmanager both contained it during the fault. Grafana's
provisioned dashboard and live alert query succeeded, and its Loki proxy returned
real log streams. The saved WARN/ERROR search contains 68 lines (at most 1000);
this count can include other operational messages within the displayed window.
Use the raw labels and messages to attribute individual symptoms.

## UTC timeline

| Event | Timestamp |
|---|---|
| Fault command started | 2026-09-29T18:43:40.359166Z |
| Prometheus activeAt (condition became active, possibly pending) | 2026-09-29T18:43:48.889371656Z |
| Alertmanager startsAt | 2026-09-29T18:44:03.889Z |
| First observed firing in both APIs | 2026-09-29T18:44:10.705809Z |
| Runbook fix started | 2026-09-29T18:44:57.139263Z |
| Selected alert absent from both APIs | 2026-09-29T18:45:07.297754Z |
| Original Bash health check returned zero | 2026-09-29T18:49:59.797602Z |
| Cleanup completed | 2026-09-29T18:49:59.823748Z |

The verifier polls every five seconds plus request time, so observations are not
exact transition times. API `activeAt` is not presented as the first firing time.
For a restart drill, a P3 naturally persists for ten minutes after recovery.
Other drills can also create expected recent-start alerts; “resolved” above
refers to the selected alert, not a claim that every unrelated alert vanished.

## Investigation, repair and verification

Followed [the service-down runbook](../runbooks/service-down.md): correlate the alert
with Service health / scrape and probe status, inspect logs, use the fault-specific undo command, then recheck
alert APIs and the original Bash monitor. Exact commands, exit statuses and
health values are in the terminal record. The CPU drill additionally has a
120-second automatic stop; the record shows when the manual fix was issued.
No error logs or metric history were cleared to make recovery pass.

## Inhibition observed during this fault

At 2026-09-29T18:44:55.896530Z Alertmanager held ServiceDown/feed active and marked
HealthProbeFailed/feed (127.0.0.1:9001), HealthProbeFailed/feed (http://127.0.0.1:9001/health) as `suppressed`, with `inhibitedBy` set to the ServiceDown fingerprint.
FeedErrorsHigh/orders stayed `active` because it belongs to a different service. Prometheus
still evaluated every rule; inhibition only mutes notifications.
[Raw Alertmanager records](../docs/evidence/phase2/stop-feed/inhibition.json).

## Evidence

- [Timeline and matching alert labels](../docs/evidence/phase2/stop-feed/timeline.json)
- [Terminal commands and health checks](../docs/evidence/phase2/stop-feed/terminal.txt)
- [Prometheus firing](../docs/evidence/phase2/stop-feed/prometheus-firing.json)
- [Alertmanager firing](../docs/evidence/phase2/stop-feed/alertmanager-firing.json)
- [Prometheus after recovery](../docs/evidence/phase2/stop-feed/prometheus-resolved.json)
- [Alertmanager after recovery](../docs/evidence/phase2/stop-feed/alertmanager-resolved.json)
- [Grafana alert query](../docs/evidence/phase2/stop-feed/grafana-firing-alerts.json)
- [Grafana Loki query](../docs/evidence/phase2/stop-feed/grafana-loki-logs.json)
- [WARN/ERROR history](../docs/evidence/phase2/stop-feed/loki-errors-warnings.json)
- [Alert state history](../docs/evidence/phase2/stop-feed/alert-history.json)

## Follow-up

Keep the recovery command next to the injection command, establish a healthy
baseline before repeating, and preserve timestamps before making changes.
Capture manual screenshots using the [exact window](../docs/screenshots/README.md).
This drill validates a small VM; it establishes no production availability SLO.
