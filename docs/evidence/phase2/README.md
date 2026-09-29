# Phase 2 real chaos evidence

These are actual fault runs in the isolated Ubuntu VM. API snapshots are
captured with curl; Grafana and Loki were also queried while the alert fired.
No screenshots, Telegram delivery or production incident claims are implied.

| Scenario | Fault start (UTC) | Firing observed | Selected alert cleared | Bash healthy |
|---|---|---|---|---|
| [fill-disk](../../../incidents/phase2-20260929-fill-disk.md) | 2026-09-29T16:56:19.291612Z | 2026-09-29T16:57:09.833535Z | 2026-09-29T16:57:26.228699Z | 2026-09-29T16:57:27.452638Z |
| [cpu-spike](../../../incidents/phase2-20260929-cpu-spike.md) | 2026-09-29T16:57:27.545944Z | 2026-09-29T16:58:53.093282Z | 2026-09-29T16:59:24.629441Z | 2026-09-29T16:59:25.740688Z |
| [slow-feed](../../../incidents/phase2-20260929-slow-feed.md) | 2026-09-29T16:59:25.780550Z | 2026-09-29T17:01:53.066472Z | 2026-09-29T17:02:54.966701Z | 2026-09-29T17:02:56.093191Z |
| [kill-feed](../../../incidents/phase2-20260929-kill-feed.md) | 2026-09-29T18:33:21.876209Z | 2026-09-29T18:34:07.449537Z | 2026-09-29T18:43:39.201441Z | 2026-09-29T18:43:40.328577Z |
| [stop-feed](../../../incidents/phase2-20260929-stop-feed.md) | 2026-09-29T18:43:40.359166Z | 2026-09-29T18:44:10.705809Z | 2026-09-29T18:45:07.297754Z | 2026-09-29T18:49:59.797602Z |
| [block-port](../../../incidents/phase2-20260929-block-port.md) | 2026-09-29T18:49:59.835288Z | 2026-09-29T18:50:25.092545Z | 2026-09-29T18:50:41.438333Z | 2026-09-29T18:55:18.063540Z |
| [net-delay](../../../incidents/phase2-20260929-net-delay.md) | 2026-09-29T18:55:18.095635Z | 2026-09-29T18:56:03.153368Z | 2026-09-29T18:56:53.776155Z | 2026-09-29T19:01:30.282058Z |
| kill-feed-aborted-20260929 — ABORTED (BrokenPipeError(32, 'Broken pipe')); rerun above | 2026-09-29T17:03:26.951503Z | — | — | — |

Each scenario directory contains baseline, firing, resolved and final healthy
API snapshots plus Grafana/Loki responses. `timeline.json` is the source for
the incident report. `poll` files are only the latest polling sample.

`step8-ci.txt` records the local CI run; synthetic Prometheus rule fixtures
are unit tests, not these real faults. Earlier step evidence remains intact.
