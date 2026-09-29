# Five-minute spoken demo

Use the Ubuntu VM `tradeops`. This is synthetic trading, with no broker or real
orders. Open Grafana, Prometheus and Alertmanager before the interview. Keep the
saved evidence available if the VM or network is unavailable. Do not promise to
complete all seven drills in five minutes: alert waiting periods and recovery
windows deliberately take longer.

## 0:00–0:40 — Purpose and architecture

“I built TradeOps Watch to practise first-level operations. A Python feed
publishes five synthetic prices. A second Python service reads them and records
BUY or SELL decisions. systemd runs both services. Prometheus pulls their metrics
and exporter metrics. Alertmanager groups and routes alerts. Alloy ships logs to
Loki, and Grafana brings metrics and logs together. Everything runs inside one
Ubuntu VM on my Apple Silicon Mac.”

Show the README diagram and the five dashboard rows.

## 0:40–1:15 — Healthy baseline

“First I establish what healthy looks like: both services and their probes are
up, prices and orders keep increasing, and the original Bash check returns zero.
An HTTP probe checks the service from outside its process; a metrics endpoint
also tells me about its internal behaviour.”

```bash
multipass exec tradeops -- sudo /opt/tradeops/scripts/healthcheck.sh
multipass exec tradeops -- systemctl is-active tradeops-feed tradeops-orders
```

## 1:15–2:30 — Detect and investigate one outage

“I will stop the feed. This is intentional fault injection in an isolated lab.
The order service will report feed errors. The rule waits before firing so a
single failed sample does not page someone.”

```bash
multipass exec tradeops -- sudo /opt/tradeops/scripts/chaos.sh stop-feed
multipass exec tradeops -- systemctl status tradeops-feed --no-pager
multipass exec tradeops -- sudo /opt/tradeops/scripts/log_search.sh errors 5
```

Show ServiceDown in Prometheus and Alertmanager after roughly 30–60 seconds.
Open the service-down runbook and Grafana’s alerts/probes/logs. In Explore, use
`{job="tradeops",service="orders"} |= "feed unreachable"` for the last 15 minutes.
Explain that a suppressed Alertmanager notification can still be visible in
Prometheus. Telegram delivery is optional and has not been tested with credentials.

## 2:30–3:15 — Recover and verify

“The runbook leads me from service status and listeners to logs, then a targeted
fix. I start the stopped feed and confirm both health endpoints recover. I also
check that the alert clears. A recent-start P3 is expected for ten minutes, and
the Bash error window may take five minutes to clear. Recovery is not just
pressing restart and assuming it worked.”

```bash
multipass exec tradeops -- sudo /opt/tradeops/scripts/chaos.sh fix-feed
multipass exec tradeops -- curl -fsS http://127.0.0.1:9001/health
multipass exec tradeops -- curl -fsS http://127.0.0.1:9002/health
```

## 3:15–4:10 — Deployment and rollback evidence

“I deploy to a versioned directory, atomically change the current symlink,
restart, and run a health gate. If the gate fails, the script restores the old
release and reports failure. I tested a good release, a deliberately broken
release and manual rollback. Here are the actual timestamps and recovery logs.
This is a single-instance restart deployment, so I do not claim zero downtime.
It also cannot reverse a database change or shared dependency update.”

Show `docs/evidence/phase2/step7-deploy-rollback.txt` and `docs/deployments.md`.
Use saved evidence here; a deliberately broken deployment can exceed this demo’s
time budget.

## 4:10–5:00 — CI, incident record and limits

“The CI workflow checks shell scripts, Python style and 39 unit tests, then
validates Compose, Prometheus rules and Alertmanager. The same script passed
locally inside Ubuntu; a hosted result requires pushing the repository. Each
incident report links real API snapshots and UTC timestamps. I separate fault
injection, detection, the fix and verified recovery. My key learning is to
correlate metrics, logs and Linux state instead of relying on one green panel.”

Open one Phase 2 incident, its evidence folder and `step8-ci.txt`. Explain the
histogram as an estimate from buckets, and mention that this is a small lab,
not a claim of production HFT experience.

## After the demo

```bash
multipass exec tradeops -- sudo /opt/tradeops/scripts/chaos.sh cleanup
# After old errors age out:
multipass exec tradeops -- sudo /opt/tradeops/scripts/healthcheck.sh
multipass exec tradeops -- sudo python3 /opt/tradeops/scripts/handover_report.py --hours 1
```
