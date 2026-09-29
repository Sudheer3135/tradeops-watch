# TradeOps Watch — Linux Monitoring & Incident Response Lab

An L1 DevOps / production support portfolio project: operate two synthetic
trading services, detect failures, debug Linux, follow runbooks, record incidents,
and hand over a shift. Built for an Apple Silicon Mac with Ubuntu in Multipass.
No real trading, broker connections, Docker, or pip in Phase 1.

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
and Git. No third-party Python packages. Both HTTP listeners are VM-local.

## Start from scratch (Mac terminal)

```bash
cd '/Users/sudheer/Desktop/TradeOps Watch'
multipass launch 24.04 --name tradeops --cpus 2 --memory 2G --disk 10G
multipass mount "$PWD" tradeops:/home/ubuntu/tradeops-watch
multipass exec tradeops -- sudo bash /home/ubuntu/tradeops-watch/scripts/install.sh
```

If the VM already exists, use `multipass start tradeops` instead of launch.
If mounting reports privileged mounts are disabled:

```bash
multipass set local.privileged-mounts=true
multipass mount "$PWD" tradeops:/home/ubuntu/tradeops-watch
```

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

## Phase 2 roadmap — not implemented

Only after explicit approval to start Phase 2: Docker Compose with Prometheus,
node_exporter, Grafana, Loki, Promtail and Alertmanager; application metrics,
Telegram routing, provisioned dashboards, GitHub Actions checks, versioned
deployment/rollback, and another evidence-backed chaos test pass.
