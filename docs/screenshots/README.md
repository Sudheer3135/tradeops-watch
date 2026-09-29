# Manual screenshot checklist

No screenshots have been taken. Use UTC in Grafana. Current VM URL:
http://192.168.2.2:3000/d/tradeops-overview (check `multipass info tradeops`).
Save images in this folder with the filenames below. History is retained for
about two days; if expired, rerun a controlled drill and record the new times.

## Historical metrics and logs from the actual runs

For each metrics image, open the linked dashboard and expand the named row.
For the logs image, open Grafana Explore, choose Loki, use
`{job="tradeops",level=~"ERROR|WARN"}` and set the identical absolute UTC window.
An empty error result is valid for a fault that did not cause application errors;
then use `{job="tradeops"}` to show continuity, and state what is visible.

| Metrics filename / dashboard | UTC From → To | Panel / expected evidence | Logs filename |
|---|---|---|---|
| [phase2-fill-disk-metrics.png](http://192.168.2.2:3000/d/tradeops-overview?from=1790700919291&to=1790701107452&timezone=utc) | 2026-09-29T16:55:19Z → 2026-09-29T16:58:27Z | System / root disk usage; fault and recovery | `phase2-fill-disk-logs.png` |
| [phase2-cpu-spike-metrics.png](http://192.168.2.2:3000/d/tradeops-overview?from=1790700987545&to=1790701225740&timezone=utc) | 2026-09-29T16:56:27Z → 2026-09-29T17:00:25Z | System / CPU and load; fault and recovery | `phase2-cpu-spike-logs.png` |
| [phase2-slow-feed-metrics.png](http://192.168.2.2:3000/d/tradeops-overview?from=1790701105780&to=1790701436093&timezone=utc) | 2026-09-29T16:58:25Z → 2026-09-29T17:03:56Z | Trading / p50, p95 and p99 latency; fault and recovery | `phase2-slow-feed-logs.png` |
| [phase2-kill-feed-metrics.png](http://192.168.2.2:3000/d/tradeops-overview?from=1790706741876&to=1790707480328&timezone=utc) | 2026-09-29T18:32:21Z → 2026-09-29T18:44:40Z | Service health / process age and restarts; fault and recovery | `phase2-kill-feed-logs.png` |
| [phase2-stop-feed-metrics.png](http://192.168.2.2:3000/d/tradeops-overview?from=1790707360359&to=1790707859797&timezone=utc) | 2026-09-29T18:42:40Z → 2026-09-29T18:50:59Z | Service health / scrape and probe status; fault and recovery | `phase2-stop-feed-logs.png` |
| [phase2-block-port-metrics.png](http://192.168.2.2:3000/d/tradeops-overview?from=1790707739835&to=1790708178063&timezone=utc) | 2026-09-29T18:48:59Z → 2026-09-29T18:56:18Z | Service health / probe failures; fault and recovery | `phase2-block-port-logs.png` |
| [phase2-net-delay-metrics.png](http://192.168.2.2:3000/d/tradeops-overview?from=1790708058095&to=1790708550282&timezone=utc) | 2026-09-29T18:54:18Z → 2026-09-29T19:02:30Z | Service health and Trading / failures and latency; fault and recovery | `phase2-net-delay-logs.png` |

## Additional screenshots

- `phase2-overview-healthy.png`: dashboard, Last 15 minutes after final recovery, all five rows; service/probes up and active alerts empty (or explain a recent-start P3).
- `phase2-slow-feed-trading.png`: the slow-feed UTC window above, Trading row; elevated p95 followed by recovery. Logs of successful slow orders use `{job="tradeops",service="orders"} |= "latency_ms="`.
- `phase2-stop-feed-alerts.png`: http://192.168.2.2:9090/alerts during a fresh stop-feed drill, once ServiceDown is firing. This page shows current alerts, not historical snapshots.
- `phase2-stop-feed-alertmanager.png`: http://192.168.2.2:9093 during that same fresh drill; show grouped alert labels and inhibition. Save the new UTC time beside the screenshot, then fix-feed and verify recovery.
- `phase2-stop-feed-logs.png`: Loki Explore with the stop-feed window above and `{job="tradeops",service="orders"} |= "feed unreachable"`; show actual dependency errors.
- `phase2-alert-history.png`: Grafana Explore / Prometheus, range query `ALERTS{alertname="HighOrderLatency",alertstate="firing"}` over the slow-feed window; show the firing interval. Active-alert tables cannot reconstruct resolved incidents.
- `phase2-deploy-rollback.png`: terminal displaying `docs/evidence/phase2/step7-deploy-rollback.txt`; include failed health gate, automatic restore and subsequent successful health result with UTC timestamps.
- `phase2-ci-success.png`: your repository's Actions page only after an actual hosted run passes. Include commit hash and green result; local CI output is not a hosted run.

Do not expose `.env`, bot tokens, passwords or chat IDs in screenshots.
