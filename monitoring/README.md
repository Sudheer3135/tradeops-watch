# TradeOps monitoring stack

Run commands inside `multipass shell tradeops`, from:

```bash
cd /home/ubuntu/tradeops-watch/monitoring
```

The Ubuntu VM needs 4 GB RAM. On the Mac, resize it while stopped:

```bash
multipass stop tradeops
multipass set local.tradeops.memory=4G
multipass start tradeops
```

Install Docker inside the VM with `sudo bash ../scripts/install_docker.sh`.
It uses Docker's official apt repository and adds `ubuntu` to the docker group.
Open a fresh VM shell afterward so group membership takes effect.

Create a private password file inside the VM (never commit it):

```bash
python3 - <<'PY'
import os
from pathlib import Path
import secrets
path = Path('.env')
if not path.exists():
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write('GRAFANA_ADMIN_PASSWORD=' + secrets.token_urlsafe(24) + '\n')
PY
docker compose config --quiet
docker compose up -d
docker compose ps
```

Grafana username is `admin`. View the locally generated password with `cat .env`
in your VM shell. Grafana saves the initial password in its persistent database;
editing the env file later does not reset an existing user's password.

On the Mac, use `multipass info tradeops` to find the current IP. At setup:

- Prometheus: http://192.168.2.2:9090
- Alertmanager: http://192.168.2.2:9093
- Grafana: http://192.168.2.2:3000
- Loki readiness (an API, not a dashboard): http://192.168.2.2:3100/ready

The UI/API ports are for the local VM lab; do not forward them to the Internet.
Application ports stay bound to VM loopback. Every monitoring container uses
Linux host networking, so `127.0.0.1` means the VM, not a separate container.
There are no `ports:` mappings in host mode. Exporter/Alloy admin listeners
bind to loopback (9100, 9115, 12345). Node exporter sees the host PID namespace
and read-only copies of `/proc`, `/sys`, and `/` to report real VM metrics.

Named volumes preserve metrics, alert state, Grafana settings, Loki chunks,
and Alloy positions across container restarts. Prometheus retains at most two
days/512 MB of blocks; Loki retention is 48 hours (deletion is asynchronous).
Each container has a memory ceiling and bounded Docker logs. Limits are guardrails,
not preallocated RAM. `docker compose down` preserves volumes; do not add `-v`
unless you deliberately want to erase the monitoring history.

All seven components run and HTTP/TCP probes monitor the original services.
Alloy ships labelled logs, Grafana provisions both data sources and the full
TradeOps dashboard, and Alertmanager supports severity routing and inhibition.
Outgoing Telegram delivery is optional; see its setup section below.

## Source documentation

- [Docker's Ubuntu apt installation](https://docs.docker.com/engine/install/ubuntu/)
- [Node exporter host-container setup](https://github.com/prometheus/node_exporter#docker)
- [Loki single-process filesystem configuration](https://grafana.com/docs/loki/latest/configure/examples/configuration-examples/)
- [Prometheus alerting rules and pending duration](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Python histogram instrumentation](https://prometheus.github.io/client_python/instrumenting/histogram/)

Image versions were selected from the projects' official GitHub release pages
on 2026-09-29 and are pinned explicitly in Compose. Actual pulled image digests
are recorded in the Phase 2 evidence; no service uses a `latest` tag.

## Step 2 metrics

The application installer creates `/opt/tradeops/venv` and installs
`prometheus-client==0.26.0`. systemd uses that interpreter. The existing
`/health`, `/prices`, response fields, fake order rule, retries, and log format
are preserved; `/metrics` is an additional route on each existing port.

| Metric | Meaning |
|---|---|
| `tradeops_prices_published_total{symbol}` | Increases once per symbol each second |
| `tradeops_last_price{symbol}` | Latest positive synthetic price |
| `tradeops_feed_up` | Publisher has started updating prices |
| `tradeops_orders_total{side}` | Number of fake BUY or SELL orders placed |
| `tradeops_order_latency_seconds` | Histogram of each order-cycle feed fetch, including slow/failed attempts |
| `tradeops_feed_errors_total` | Failed or too-slow feed fetches |
| `tradeops_last_successful_price_fetch_timestamp` | Unix timestamp of last accepted fetch |

One cycle normally places five orders, but records one fetch-latency observation.
Histogram buckets span 1 ms–2 s (plus the automatic infinity bucket). Failed
cycles are included so a degraded dependency does not disappear from latency
monitoring. Orders still reject fetches slower than 400 ms, just as in Phase 1.
A healthy-but-slow 300–400 ms fetch can therefore trigger latency monitoring
without changing the health API policy. Counters reset when a process restarts;
Prometheus `rate()` handles those resets.

```bash
curl -fsS http://127.0.0.1:9001/metrics
curl -fsS http://127.0.0.1:9002/metrics
sudo /opt/tradeops/venv/bin/python ../scripts/verify_metrics.py
```

The last command deliberately stops the feed for three seconds and restores it
in a `finally` block. It verifies HTTP 503 during dependency failure while the
order service's metrics endpoint remains accessible.

## Step 3 alert rules and review gate

Every rule includes severity, team `tradeops`, service identity from its input
metrics, and a relative `runbooks/*.md` annotation. Open that path in this repo.

| Alert | Condition and waiting period |
|---|---|
| ServiceDown, P1 | Any configured scrape is down for 15 seconds |
| HealthProbeFailed, P1 | HTTP/TCP probe fails for 15 seconds |
| NoPricesFlowing, P1 | One-minute publication rate remains zero for a further minute |
| FeedErrorsHigh, P2 | Two-minute average above 0.1 errors/sec for 30 seconds |
| HighOrderLatency, P2 | One-minute p95 above 300 ms for 2 minutes |
| HighCPU, P2 | One-minute aggregate CPU usage above 85% for 30 seconds |
| HighMemory, P2 | Usage based on MemAvailable above 85% for 2 minutes |
| DiskAlmostFull, P2 | Root usage 85–below 95% for 30 seconds |
| DiskAlmostFull, P1 | Root usage at least 95% for 15 seconds |
| ServiceRestartedRecently, P3 | Process started within 10 minutes, observed for 30 seconds |

Recent-start P3 alerts include first startup and intentional restarts. They do
not prove a crash; correlate with `journalctl` and the Phase 1 restart counter.
A five-second feed crash can be shorter than the P1 waiting period; P3 still
records its new process start. Disk calculations use space available to ordinary
users and may differ slightly from rounded `df` percentages.

```bash
docker compose exec -T prometheus promtool check rules /etc/prometheus/rules/tradeops-alerts.yml
docker compose exec -T prometheus promtool check config /etc/prometheus/prometheus.yml
docker compose exec -T prometheus promtool test rules /etc/prometheus/rules-tests.yml
curl -fsS http://127.0.0.1:9090/api/v1/alerts
curl -fsS http://127.0.0.1:9093/api/v2/alerts
```

`rules-tests.yml` contains synthetic unit-test input, not incident evidence.
It covers all ten rules, pending periods, disk severity boundaries, expiry of
the recent-start window, and a short scrape failure that must not fire.
The real live APIs are captured separately under `docs/evidence/phase2/`.

Both requested review gates were approved. Real chaos evidence is indexed in
`../docs/evidence/phase2/README.md`; unit fixtures are not incident evidence.

## Step 4: optional Telegram and inhibition

Severity routing and service-scoped inhibition are now configured. Follow
[the secret-file setup guide](../docs/telegram-setup.md) to enable Telegram.
Until then, alerts are routed to receivers without outgoing integrations and
remain visible in the UI. Configuration and inhibition are verified; Telegram
delivery is not claimed as tested.

## Step 5: logs

Alloy now tails `/var/log/tradeops/*.log`, derives the service from the filename,
extracts the timestamp and severity, and sends logs to Loki. Application names
are normalized to `feed` and `orders`. Alert severities P1/P2/P3 become
ERROR/WARN/INFO; cron exit 2/1/0 maps the same way. Unrecognized lines use UNKNOWN.
The raw line stays intact. File read positions use the Alloy named volume.
See the eight tested LogQL examples in [README](../README.md) and
[LEARNING](../LEARNING.md). Their machine-readable source is `logql-examples.json`.

## Step 6: TradeOps Overview

Open http://192.168.2.2:3000/d/tradeops-overview (login: `admin`, password in
VM `monitoring/.env`). The dashboard loads from the version-controlled JSON;
no manual data-source or panel setup is needed. It includes five rows: service
health, trading, system, current alerts, and WARN/ERROR logs. Times are UTC.

Set **Last 30 minutes**, refresh **15s**. An empty alerts table means no current
firing alerts; an empty logs panel means no matching lines in that time range.
The current dashboard's links use this VM IP; update them if Multipass assigns
a different address. `scripts/verify_dashboard.py` checks provisioning and runs
all 19 queries through Grafana; screenshots remain a manual Step 9 task.

## Step 7: releases

See [deployment and rollback instructions](../docs/deployments.md). systemd now
runs application code through `/opt/tradeops/current`; stable monitoring and
recovery tools remain in `/opt/tradeops/scripts`. Deployment logs are included
in Alloy's existing `*.log` discovery and appear with service label `deploy`.
