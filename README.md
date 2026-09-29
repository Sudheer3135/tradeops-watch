# TradeOps Watch — Linux Monitoring & Incident Response Lab

An L1 DevOps / production support portfolio project: operate two synthetic
trading services, detect failures, debug Linux, follow runbooks, record incidents,
and hand over a shift. Built for an Apple Silicon Mac with Ubuntu in Multipass.
No real trading or broker connections. Phase 1 used only the Python standard
library and Bash; the current Phase 2 checkpoint adds Docker monitoring and
a Python metrics dependency while preserving the Phase 1 operations tools.

**Phase 2 checkpoint: Steps 0–3.** See [monitoring setup and URLs](monitoring/README.md)
and [progress/evidence](docs/phase2-progress.md). Later steps require the requested review.

```text
MacBook M2 -> Multipass Ubuntu 24.04 (tradeops)
                 systemd -> feed :9001 <- orders :9002
                                |             |
                                +---- logs ---+
                 cron -> healthcheck -> alerts + active state
                          |                  |
                       runbooks        handover report
                 chaos -> diagnose -> fix -> verify -> incident
```

[Architecture details](docs/architecture.md) · [Interview guide](LEARNING.md)

## Tech used

Python 3 standard library (`http.server`, `urllib`, `logging`, threads), Bash,
Ubuntu 24.04 ARM64, systemd, cron, curl, iproute2/ss/tc, iptables, logrotate,
and Git. Phase 2 adds pinned `prometheus-client` in a virtual environment and
seven pinned monitoring containers. Both application HTTP listeners remain VM-local.

## Start from scratch (Mac terminal)

```bash
cd '/Users/sudheer/Desktop/TradeOps Watch'
multipass launch 24.04 --name tradeops --cpus 2 --memory 4G --disk 10G
multipass mount "$PWD" tradeops:/home/ubuntu/tradeops-watch
multipass exec tradeops -- sudo bash /home/ubuntu/tradeops-watch/scripts/install.sh
```

If the VM already exists, use `multipass start tradeops` instead of launch.
If mounting reports privileged mounts are disabled:

```bash
multipass set local.privileged-mounts=true
multipass mount "$PWD" tradeops:/home/ubuntu/tradeops-watch
```

On this Mac, the mount was created but reads failed with `Operation not permitted`
(macOS Desktop privacy protection). The tested fallback below copies the source
without changing global privacy permissions:

```bash
multipass umount tradeops:/home/ubuntu/tradeops-watch
COPYFILE_DISABLE=1 tar --exclude=.git --exclude=__pycache__ -czf /tmp/tradeops-watch-source.tar.gz .
multipass transfer /tmp/tradeops-watch-source.tar.gz tradeops:/home/ubuntu/tradeops-watch-source.tar.gz
multipass exec tradeops -- bash -lc 'mkdir -p /home/ubuntu/tradeops-watch && tar --no-same-owner -xzf /home/ubuntu/tradeops-watch-source.tar.gz -C /home/ubuntu/tradeops-watch'
multipass exec tradeops -- sudo bash /home/ubuntu/tradeops-watch/scripts/install.sh
```

Repeat the archive/transfer/extract steps after editing source on the Mac, then
rerun install. This is a copy, so VM evidence must also be copied back with
`multipass transfer`. If you prefer a live mount, grant Multipass access in
macOS System Settings → Privacy & Security → Full Disk Access, restart Multipass,
and retry mounting; that broader permission was not changed for this project.

Alternative: after publishing, clone the repository inside the VM at
`/home/ubuntu/tradeops-watch`, then run the same installer. The installer is
safe to rerun; it restarts both services to load changes. Service code lives in
`/opt/tradeops`, logs in `/var/log/tradeops`, monitor state in `/var/lib/tradeops`.
Times in application logs, alerts, and reports are UTC.

## Quick demo (Mac terminal)

```bash
multipass exec tradeops -- systemctl --no-pager status tradeops-feed tradeops-orders
multipass exec tradeops -- curl -fsS http://127.0.0.1:9001/prices
multipass exec tradeops -- curl -fsS http://127.0.0.1:9002/health
multipass exec tradeops -- sudo /opt/tradeops/scripts/healthcheck.sh
multipass exec tradeops -- sudo /opt/tradeops/scripts/log_search.sh latency
multipass exec tradeops -- sudo /opt/tradeops/scripts/handover_report.py --hours 8
```

For a failure demo, open `multipass shell tradeops`, then use these commands
**inside the VM**. Run only one drill at a time.

| Break command (prefix `sudo /opt/tradeops/scripts/chaos.sh`) | Expected check | Fix subcommand |
|---|---|---|
| `kill-feed` | P1 if checked during outage; P2 `restart-feed` after recovery | `fix-feed` (normally auto-restarts in 5s) |
| `stop-feed` | P1 `service-feed`, missing port and HTTP | `fix-feed` |
| `fill-disk` | P2 `disk`, default 85% | `fix-disk` |
| `cpu-spike` | P2 `cpu`, default 85% | `fix-cpu` (also expires automatically) |
| `block-port` | P1 HTTP failure while listener still exists | `fix-port` |
| `net-delay` | Slow/unreachable feed; degraded orders and/or HTTP timeout | `fix-delay` |

```bash
sudo /opt/tradeops/scripts/chaos.sh stop-feed
sleep 5
sudo /opt/tradeops/scripts/healthcheck.sh
echo "Exit code: $?"                 # 2 = critical, 1 = warning, 0 = healthy
sudo /opt/tradeops/scripts/log_search.sh alerts
sudo /opt/tradeops/scripts/log_search.sh errors 5
# Follow runbooks/service-down.md, then:
sudo /opt/tradeops/scripts/chaos.sh fix-feed
sleep 4
sudo /opt/tradeops/scripts/healthcheck.sh
sudo /opt/tradeops/scripts/chaos.sh cleanup
```

Cron runs the same check every minute. For a quick demo we invoke it directly,
so detection does not depend on where the minute boundary falls. Repeated alerts
are suppressed for ten minutes per check; **active state and exit status still
update**. Read `/var/lib/tradeops/active-alerts` for the current problems.
An error-rate warning remains until old errors leave the five-minute window.
Recovery itself does not send a Telegram notification.

The CPU drill uses bounded systemd workers; disk allocation leaves at least
600 MiB free at allocation time. Cleanup removes only the tagged firewall rule,
lab-created loopback qdisc, CPU unit, and known filler file, then starts services.
The hostname and Linux guard prevent accidentally running chaos on macOS.

## Monitoring settings

Defaults at the top of `scripts/healthcheck.sh`: CPU, memory and root disk 85%;
more than 5 ERROR lines in the last 5 minutes; notification cooldown 600 seconds.
A diagnostic override can be passed with `sudo env CPU_THRESHOLD=90 ...`.
Use only nonnegative integer threshold values. Persistent changes require
editing the source and rerunning install. Exit 0 is healthy, 1 warning, 2 critical.
P3 is reserved for future informational checks; current checks use P1/P2.

Optional Telegram: create root-owned `/etc/tradeops/alert.env` with mode 600,
containing `TELEGRAM_BOT_TOKEN='...'` and `TELEGRAM_CHAT_ID='...'`. This is trusted
shell configuration. Missing credentials skip delivery silently. Never commit
this file. Telegram delivery has not been tested without a configured recipient.

## Runbooks and actual incidents

- [Service down](runbooks/service-down.md)
- [Disk usage](runbooks/disk-full.md)
- [CPU / memory](runbooks/high-cpu.md)
- [Blocked port / network delay](runbooks/port-blocked.md)
- [Incident reports](incidents/)
- [Raw evidence](docs/evidence/)

Run the complete fault/recovery suite again (changes this disposable lab):

```bash
multipass exec tradeops -- sudo bash /home/ubuntu/tradeops-watch/scripts/verify_lab.sh
```

Each scenario must produce a nonzero health result and then return to health.
The script preserves raw output in `docs/evidence/<scenario>.txt`, stops on a
failed check, and cleans up when it exits. Historical error windows can make a
full run take several minutes. Rerunning replaces the raw evidence; refresh
incident reports if you publish results from a new run.

## Publish to GitHub (Mac terminal)

```bash
cd '/Users/sudheer/Desktop/TradeOps Watch'
gh auth login
gh repo create tradeops-watch --public --source=. --remote=origin --push
```

This creates a **public** portfolio repository. Use `--private` if preferred.
The repository is committed locally; creation/push is left to you.

## Verified Phase 1 results

All six drills passed on 2026-09-29 in the actual Ubuntu VM. Each record shows
fault detection, diagnosis, repair, and a final healthy result.

| Verified behavior | Proof |
|---|---|
| Installer runs twice; both services enabled and active | [install](docs/evidence/install.txt), [rerun](docs/evidence/install-rerun.txt) |
| Five changing prices, increasing orders, health and 404 routes | [HTTP checks](docs/evidence/http-api.txt) |
| SIGKILL detected; automatic restart observed | [kill-feed](docs/evidence/kill-feed.txt) |
| Intentional service stop detected and repaired | [stop-feed](docs/evidence/stop-feed.txt) |
| Disk 88% triggers warning; cleanup returns it to 24% | [fill-disk](docs/evidence/fill-disk.txt) |
| CPU 100% triggers warning; worker cleanup restores health | [cpu-spike](docs/evidence/cpu-spike.txt) |
| Firewall rejection detected despite open listener | [block-port](docs/evidence/block-port.txt) |
| Real 500 ms netem delay detected; qdisc removed | [net-delay](docs/evidence/net-delay.txt) |
| Cron runs, memory threshold override works, repeat alert suppressed | [monitor checks](docs/evidence/monitor-checks.txt), [cron](docs/evidence/cron.txt) |
| Handover distinguishes active issues from recovery | [open issue](docs/evidence/handover-open-issue.txt), [recovered report](docs/evidence/handover.txt) |
| CPU workers stop automatically at 120s; repeated cleanup leaves no changes | [automatic expiry](docs/evidence/cpu-auto-timeout.txt) |
| Final state: services healthy, no active alerts, no chaos artifacts | [final state](docs/evidence/final-state.txt), [final handover](docs/evidence/final-handover.txt) |
| macOS chaos invocation refuses to run | [safety guard](docs/evidence/macos-safety-guard.txt) |

[Testing methods and limitations](docs/TESTING.md) · [Six incident reports](incidents/README.md)

## Sample alerts copied from the actual run

```text
2026-09-29T11:17:24Z | P1 | service-feed | service inactive | runbooks/service-down.md
2026-09-29T11:18:10Z | P2 | disk | Disk 88% >= 85% | runbooks/disk-full.md
2026-09-29T11:18:21Z | P2 | cpu | CPU 100% >= 85% | runbooks/high-cpu.md
```

## Sample shift handover copied from the actual run

```markdown
# TradeOps shift handover

Window (UTC): 2026-09-29T03:23:34.074921+00:00 to 2026-09-29T11:23:34.074921+00:00

## Services now
- tradeops-feed: active
- tradeops-orders: active

## Alerts by severity
- P1: 4 notifications; service-feed (1), port-9001 (1), http-9001 (1), http-9002 (1)
- P2: 4 notifications; restart-feed (1), disk (1), cpu (1), error-rate (1)
- P3: 0 notifications; none

## Open issues (latest health check)
- None in latest snapshot.

## Resolved issues
- cpu: absent from latest check
- disk: absent from latest check
- error-rate: absent from latest check
- http-9001: absent from latest check
- http-9002: absent from latest check
- port-9001: absent from latest check
- restart-feed: absent from latest check
- service-feed: absent from latest check

## Top errors
- 8 × feed unreachable: <urlopen error [Errno 111] Connection refused>
- 1 × feed unreachable: feed slow: 2174.66 ms
- 1 × feed unreachable: feed slow: 2060.29 ms
- 1 × feed unreachable: feed slow: 2090.21 ms
- 1 × feed unreachable: feed slow: 2088.12 ms

## Notes for next shift
- Confirm both HTTP health endpoints and review active alerts.
- An error-rate alert may persist for 5 minutes after recovery.
- Read incidents/ and record owner, next action, and escalation for any unresolved issue.
```

## Phase 2 checkpoint and remaining work

Steps 0–3: Phase 1 reviewed; Docker stack runs in the 4 GB Ubuntu VM; both
services expose metrics; ten Prometheus rules have validation and unit tests.
The existing APIs and Phase 1 monitoring scripts have real regression evidence.

Open [monitoring/README.md](monitoring/README.md) for setup, credentials handling,
metric definitions, alert thresholds and review commands. The live stack uses
Grafana Alloy, not Promtail. Alloy log shipping is pending Step 5.

Remaining after review: Telegram severity routing and inhibition; Alloy log
parsing; TradeOps dashboard; deployment/automatic rollback; GitHub Actions and
unit tests; seven complete chaos runs; screenshots checklist; updated interview
questions, spoken demo, and evidence-backed resume bullets.

The original Phase 1 evidence remains in `docs/evidence/`. New evidence is in
`docs/evidence/phase2/`; synthetic rule fixtures are explicitly identified and
are not represented as real incidents.


## Eight useful LogQL queries

In Grafana Explore select **Loki** and set the time picker to **Last 15 minutes**.
The time picker limits log searches; `[15m]` in a metric query is its counting
window. Empty results can be correct when no matching event occurred.

1. Errors in the last 15 minutes:

```logql
{job="tradeops",level="ERROR"}
```

2. Error count per service:

```logql
sum by (service) (count_over_time({job="tradeops",level="ERROR"}[15m]))
```

3. Feed dependency errors:

```logql
{job="tradeops"} |= "feed unreachable"
```

4. Five most common error messages:

```logql
topk(5, sum by (message) (count_over_time({job="tradeops",level="ERROR"} | pattern `<timestamp> | <_> | <message>` [15m])))
```

5. Orders taking more than 100 ms:

```logql
{job="tradeops",service="orders"} |= "latency_ms=" | regexp `latency_ms=(?P<latency_ms>[0-9.]+)` | latency_ms > 100 | __error__=""
```

6. Fake BUY orders:

```logql
{job="tradeops",service="orders"} |= "side=BUY"
```

7. Warnings and errors together:

```logql
{job="tradeops",level=~"ERROR|WARN"}
```

8. Log lines per second by service:

```logql
sum by (service) (rate({job="tradeops"}[1m]))
```

Only job, service and level are intentionally indexed here; message text is parsed
at query time. Do not make every order ID or error message an ingestion label.
Alloy also preserves the original file timestamp and maps P1/P2/P3 alert lines
to ERROR/WARN/INFO; unfamiliar formats are labelled UNKNOWN.
