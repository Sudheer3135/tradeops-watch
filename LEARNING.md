# TradeOps Watch interview notes

## What each file does

- `services/market_feed.py`: makes five fictional prices every second; answers HTTP requests; rotates its own logs.
- `services/order_service.py`: reads those prices every two seconds, records fictional orders, measures request latency, and keeps retrying if the feed fails. BUY when price is no higher than last time; SELL otherwise.
- `systemd/tradeops-feed.service`: runs the feed as an unprivileged user and restarts crashes after five seconds.
- `systemd/tradeops-orders.service`: starts orders after the feed and restarts crashes. Ordering does not guarantee readiness.
- `scripts/install.sh`: creates folders/user, copies code, installs packages/configuration, starts services. Running twice updates the same installation.
- `scripts/healthcheck.sh`: checks services, listening ports, HTTP, restarts, CPU, memory, disk, and recent errors. Saves active problems and limits repeated notifications to once per ten minutes.
- `scripts/log_search.sh`: filters recent errors, ranks error messages, calculates order latency, follows logs, and shows today's alerts.
- `scripts/chaos.sh`: injects a failure only in the named Linux VM; each failure has a fix. Cleanup removes lab changes.
- `scripts/handover_report.py`: summarizes one shift from timestamped logs and the latest monitoring snapshot; prints and saves Markdown.
- `scripts/verify_monitor.sh`: checks threshold overrides, notification deduplication, cron output, log tools, service settings and report generation.
- `scripts/verify_lab.sh`: runs real fault/recovery cycles and records exact output. It stops on a failed assertion and cleans up.
- `cron/tradeops-cron`: schedules the health check every minute as root.
- `runbooks/service-down.md`: how to investigate stopped or crashing services.
- `runbooks/disk-full.md`: how to find disk usage and remove the known lab filler.
- `runbooks/high-cpu.md`: how to identify CPU/memory pressure and stop the lab workers.
- `runbooks/port-blocked.md`: how to distinguish missing listeners, firewall failures, and delay.
- `incidents/*.md`: reports based on actual timestamped drill output, not invented production incidents.
- `docs/TESTING.md`: explains what was actually tested, preserved setup failures, and limits of the evidence.
- `incidents/README.md`: links the six real drill reports.
- `docs/architecture.md`: the VM, service, monitoring, and log relationships.
- `docs/evidence/*.txt`: raw command output proving what was run and observed.
- `README.md`: setup, demo, evidence links and Phase 2 status.
- `scripts/install_docker.sh`: installs Docker Engine and Compose from Docker's official apt repository.
- `monitoring/docker-compose.yml`: the seven pinned monitoring containers, host networking, memory limits and named volumes.
- `monitoring/prometheus/`: scrape targets, the ten alert rules and their promtool unit tests.
- `monitoring/alertmanager/alertmanager.yml`: severity routes and the two ServiceDown inhibition rules.
- `monitoring/alloy/config.alloy` and `monitoring/loki/`: log shipping, level parsing and 48-hour log storage.
- `monitoring/grafana/`: provisioned data sources and the TradeOps Overview dashboard.
- `scripts/configure_telegram.py`: builds and validates an optional Telegram receiver from ignored secret files.
- `scripts/deploy.sh`, `scripts/rollback.sh`, `scripts/deploy_common.sh`: versioned releases, health gate, automatic/manual rollback and retention.
- `scripts/verify_stack.py`, `verify_metrics.py`, `verify_dashboard.py`, `verify_deploy.sh`: live checks that save Phase 2 evidence.
- `scripts/verify_chaos.py`: runs each fault, waits for the alert in Prometheus and Alertmanager, applies the fix and waits for recovery; stop-feed also records real inhibition.
- `scripts/summarize_chaos.py`: turns the saved chaos timelines into incident reports, the evidence index and the screenshot checklist.
- `scripts/ci_check.sh` and `.github/workflows/ci.yml`: the lint, test and configuration checks run locally and on GitHub.
- `tests/`: 39 pytest cases for prices, order rule, alert formatting and handover parsing.
- `docs/demo-script.md`, `docs/resume-bullets.md`: five-minute spoken demo and evidence-backed resume lines.
- `LEARNING.md`: this interview guide.
- `.gitignore`: keeps credentials, Python caches, and temporary files out of Git.

## Commands used in this project

Commands below run inside Ubuntu unless marked Mac. `sudo` runs a command with
administrator rights. Paths beginning `/` start at the filesystem root.

| Command | Meaning | Example |
|---|---|---|
| multipass (Mac) | Create/control Ubuntu VMs | `multipass exec tradeops -- hostname` |
| uname | Operating system/architecture | `uname -a` |
| hostname | Machine name used by the safety guard | `hostname` |
| sudo | Run with administrator rights | `sudo systemctl status tradeops-feed` |
| bash | Run a Bash script | `bash scripts/install.sh` |
| python3 | Run Python without pip | `python3 scripts/handover_report.py --hours 8` |
| apt-get | Install Ubuntu packages | `sudo apt-get install curl` |
| id | Check a user exists | `id tradeops` |
| useradd | Create a service account | `sudo useradd --system --shell /usr/sbin/nologin tradeops` |
| install | Copy with explicit permissions or make folders | `sudo install -d /opt/tradeops` |
| mkdir | Create folders | `mkdir -p docs/evidence` |
| chown | Change ownership | `sudo chown tradeops:tradeops /var/log/tradeops` |
| chmod | Change permissions | `chmod +x scripts/healthcheck.sh` |
| touch | Create empty file/update timestamp | `touch /tmp/example` |
| tar | Archive/extract source for VM transfer | `tar -czf /tmp/source.tar.gz services scripts` |
| cp | Copy a file | `cp README.md /tmp/readme-copy.md` |
| mv | Rename/replace a file | `mv /tmp/report.tmp /tmp/report.md` |
| rm | Remove only a known file | `sudo rm -f /var/lib/tradeops/disk-fill` |
| cd / pwd | Change/show directory | `cd /opt/tradeops; pwd` |
| dirname | Parent directory of a path | `dirname /opt/tradeops/scripts/install.sh` |
| ls | List files | `ls -l /var/log/tradeops` |
| cat | Print a file | `cat /var/lib/tradeops/active-alerts` |
| head / tail | First/last lines; follow updates | `tail -F /var/log/tradeops/alerts.log` |
| tee | Print and append to a file | `echo example | tee -a /tmp/example.log` |
| echo / printf | Print text | `printf '%s\n' hello` |
| date | Format timestamps or subtract time | `date -u -d '5 minutes ago' +%FT%TZ` |
| sleep | Pause briefly | `sleep 5` |
| systemctl | Inspect/control systemd services | `systemctl show tradeops-feed -p NRestarts` |
| journalctl | Read systemd logs | `journalctl -u tradeops-feed --since '10 minutes ago'` |
| systemd-run | Create a temporary managed service | `sudo systemd-run --unit=example /usr/bin/sleep 10` |
| ss | Show sockets/listeners | `sudo ss -tulpn` |
| curl | Send HTTP requests; timeout/fail on errors | `curl -fsS --max-time 2 http://127.0.0.1:9001/health` |
| df | Filesystem space usage | `df -h /` |
| du | Size used by directories/files | `sudo du -sh /var/log/tradeops` |
| free | Memory usage | `free -m` |
| top | Live or batch process overview | `top -b -n 1` |
| pgrep | Find a process by name | `pgrep -x yes` |
| ps | Process list and states | `ps -eo pid,user,stat,pcpu,pmem,args --sort=-pcpu` |
| kill | Send a signal to a specific PID | `kill -TERM 1234` (only after checking PID) |
| timeout | Limit a command's runtime | `timeout 120 sleep 300` |
| yes | Produce repeated output; here burns CPU | `timeout 2 yes > /dev/null` |
| nproc | Number of available CPUs | `nproc` |
| fallocate | Allocate disk space quickly | `fallocate -l 1M /tmp/example-fill` |
| iptables | Inspect or change firewall rules | `sudo iptables -L OUTPUT -n -v` |
| tc | Inspect or change traffic control | `tc qdisc show dev lo` |
| logrotate | Validate/rotate non-Python logs | `sudo logrotate -d /etc/logrotate.d/tradeops` |
| flock | Avoid overlapping checks | `flock -n /tmp/demo.lock echo locked` |
| mktemp | Create a unique temporary file | `mktemp /tmp/demo.XXXXXX` |
| awk | Extract fields and calculate | `awk '/MemTotal/{print $2}' /proc/meminfo` |
| grep | Match text | `grep ERROR /var/log/tradeops/order_service.log` |
| sort | Sort lines | `sort /tmp/example.log` |
| uniq | Count adjacent identical lines | `sort /tmp/example.log | uniq -c` |
| wc | Count lines | `wc -l /var/log/tradeops/alerts.log` |
| tr | Translate/remove characters | `echo '85%' | tr -dc '0-9'` |
| seq | Generate a sequence | `seq 1 3` |
| read | Read fields into shell variables | `read -r value < /var/lib/tradeops/last-check` |
| source | Load trusted shell configuration | `source /etc/tradeops/alert.env` |
| exec | Open lock file descriptor/replace process | `exec 9>/tmp/demo.lock` |
| trap | Run cleanup when a script exits | `trap 'echo finished' EXIT` |
| set / shopt | Configure Bash error handling/globbing | `set -euo pipefail` |
| true / false | Return success/failure | `false || true` |
| git (Mac) | Track small source changes | `git log --oneline` |
| gh (Mac) | Create GitHub repository and push | `gh repo create tradeops-watch --public --source=. --remote=origin --push` |

`|` sends output to the next command; `>` overwrites a file; `>>` appends;
`2>&1` includes error output; `&` runs a process in the background; `wait`
waits for children. `if`, `case`, `for`, `while`, and `return` are Bash control
flow, not separate installed programs. `[[ ... ]]` and `(( ... ))` test text
and arithmetic. `exit` sets a command's status for scripts/cron.

## 25 likely interview questions

1. **What did you build?** A small Ubuntu operations lab with two fake trading services, monitoring, failure drills, runbooks, real incident evidence, and shift reports.
2. **Why a VM on your Mac?** It supplies real Linux systemd, cron, `/proc`, iptables and tc without changing macOS.
3. **What is systemd?** Linux's service manager. My unit files choose the user, command, startup ordering, and restart policy.
4. **What does Restart=on-failure mean?** Restart abnormal exits, including SIGKILL, after five seconds. An intentional `systemctl stop` stays stopped.
5. **Does After= mean the feed is ready?** No. It orders startup jobs. My order worker still retries when HTTP is unavailable.
6. **How do you investigate a service failure?** Check `systemctl status`, the journal, application logs, listeners, and HTTP; use the service-down runbook.
7. **What is journalctl?** It reads systemd's journal. `journalctl -u tradeops-feed` shows startup and crash details for that unit.
8. **How does cron work?** Five time fields schedule a command. In `/etc/cron.d`, a user field follows them. Five stars means every minute.
9. **What is a port?** A number identifying a network endpoint on an IP address. My feed uses TCP 9001; orders health uses TCP 9002.
10. **What is TCP/IP here?** IP addresses identify endpoints; TCP provides an ordered byte stream; HTTP carries requests over it. `127.0.0.1` stays within this VM.
11. **ss versus netstat?** Both show sockets. `ss` is the modern Linux tool used here; `-tulpn` shows TCP/UDP listeners, numeric addresses, and process information.
12. **Why check both port and HTTP?** A listener can exist while the application or a dependency is unhealthy. Orders return 503 when the feed is degraded.
13. **How do you handle disk full?** Check `df`, locate growth with `du`, identify safe cleanup, recover space, and verify writes and monitoring. My drill removes only its known filler file.
14. **How do you handle high CPU?** Use `top` and `ps` to identify the process and impact before stopping it. My bounded workers have a timer and explicit cleanup.
15. **How is CPU measured?** Compare total and idle counters in `/proc/stat` across one second. Aggregate CPU can hide one busy core on a larger machine.
16. **How is memory measured?** Use MemAvailable versus MemTotal, so reclaimable cache is not mistaken for fully consumed memory.
17. **What are process states?** R runnable/running, S interruptible sleep, D uninterruptible wait, T stopped, Z zombie. A zombie needs its parent to reap it; killing it again does not help.
18. **SIGTERM versus SIGKILL?** TERM requests graceful shutdown; KILL cannot be caught and prevents cleanup. The crash drill uses KILL deliberately; normal recovery uses systemctl.
19. **Why rotate logs?** Prevent unbounded disk growth. Python rotates application logs at 2 MB; logrotate handles alert/cron logs. Two rotators must not own the same file.
20. **What does iptables do in the drill?** It rejects loopback TCP traffic to port 9001 using a tagged OUTPUT rule. Cleanup removes that rule only.
21. **What is latency and how do you test it?** Time from request start to completed response, measured with a monotonic clock in milliseconds. tc adds loopback delay; orders mark feed requests over 400 ms unhealthy.
22. **How do you avoid alert spam?** Store each check's last notification timestamp, wait ten minutes between repeats, and maintain active state separately. This does not suppress the unhealthy exit status.
23. **What do P1/P2/P3 and exit codes mean?** In this lab P1 means unavailable/degraded service (exit 2); P2 means resource/error/restart warning (exit 1). P3 is reserved; healthy is exit 0. These are lab policy, not a claim about any firm's policy.
24. **When do you escalate?** Immediately for live trading impact or failed recovery, to the on-call SRE/application/network owner. Provide UTC timeline, scope, logs, changes, attempts, current state, and next action.
25. **What belongs in shift handover?** Shift window, service status, severity counts, open and resolved issues, top errors, and named next actions. My report warns if the monitoring snapshot is stale; human owners and business context still need adding.

## Honest limitations to mention

This is a single-VM practice project, not an HFT trading platform. It does not
measure exchange latency, execute real orders, or provide redundant monitoring.
Cron can miss brief HTTP failures; restart counters partly cover crashes.
Service status alone cannot prove application health. Alert counts are
notifications after deduplication, not every failed poll. Five-minute error
windows intentionally delay full recovery status. Disk safety is a preallocation
check, not a reservation against other concurrent writers. Telegram is optional
and needs a real destination to test delivery. Read the evidence before describing
any capability as tested.


## Phase 2 first checkpoint (Steps 1–3)

- Docker Engine runs the monitoring programs in containers inside Ubuntu.
  The VM still provides the real Linux kernel; Docker does not replace it.
- `scripts/install_docker.sh` installs Docker from its official Ubuntu apt
  repository. `monitoring/docker-compose.yml` starts seven pinned images.
- Prometheus pulls numerical metrics every 15 seconds. `service` labels let
  us connect application scrapes, HTTP probes and alerts for the same service.
- node_exporter reads the VM's real CPU/memory/filesystem using read-only host
  mounts. blackbox_exporter tests HTTP and TCP from outside the application.
- `/opt/tradeops/venv` isolates `prometheus-client==0.26.0` from system Python.
  The application installer can be run again without duplicating the setup.
- A counter increases until a process restarts; a gauge reports a current
  value; a histogram counts observations in latency buckets. The order-cycle
  histogram measures one fetch attempt, not each of the five orders it produces.
- `rate(counter[1m])` estimates growth per second and handles counter resets.
  `histogram_quantile(0.95, ...)` estimates p95 from bucket rates, so it is an
  approximation whose resolution depends on the bucket boundaries.
- Alert `for:` is a continuous waiting period: the condition must remain true
  throughout it. A rate window is additional smoothing, not the same timer.
- A `P3` recent-start notification also covers a normal deployment or first
  startup. It is a clue to investigate, not proof of a crash.
- `scripts/verify_stack.py` checks live readiness/probes/targets.
  `scripts/verify_metrics.py` checks real metrics, old APIs and recovery from
  a three-second feed outage. `monitoring/prometheus/rules-tests.yml` supplies
  synthetic time series for promtool; those are unit tests, not real incidents.
- Named volumes retain data after restart. Host networking lets containers
  access the same VM loopback addresses as the original systemd services.

The full file guide is at the top of this page; questions 26–50 follow below.


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


## Phase 2 Steps 4–7: what to explain

- `configure_telegram.py` reads ignored secret files and validates a private
  generated receiver config before enabling it. The token stays in a file.
  Without credentials, Alertmanager still shows alerts but sends no messages.
- Alertmanager groups related alerts so one incident does not generate a message
  for every sample. Inhibition suppresses notifications for dependent symptoms;
  it does not delete metrics or remove the problem from Prometheus.
- Alloy reads existing log files and remembers its position in a named volume.
  Loki stores logs; Grafana queries them. Labels narrow a search before LogQL
  filters or parses the message text.
- Grafana provisioning creates data sources and the dashboard from Git-tracked
  files. `verify_dashboard.py` tests the dashboard through Grafana's API and
  data-source proxies; this is not a screenshot or visual layout review.
- `deploy.sh` copies service code into an immutable release directory, changes
  a symlink, restarts the services and runs the original health gate. A failed
  deployment returns nonzero even when automatic recovery succeeds.
- `rollback.sh` selects the previous healthy release. `deploy_common.sh` supplies
  the lock, atomic symlink change, health polling, logging and retention helpers.
  Current and previous releases are protected while keeping three managed copies.
- `verify_deploy.sh` uses a temporary broken source fixture, never corrupts the
  repository services, and proves good deploy, rejection, automatic rollback,
  explicit rollback and retention with real running processes.
- A symlink rollback restores code quickly but does not undo a database schema
  change or a shared Python dependency update. This lab pins shared dependencies
  and rejects deploys with a changed requirements file.
- Blue-green would run two environments and switch traffic between them. This
  lab restarts a single environment, so it has brief downtime and makes no
  zero-downtime claim.

## Phase 2: 25 more interview questions (26–50)

**26. How does Prometheus get this project's metrics?**  
It pulls HTTP `/metrics` endpoints every 15 seconds. The applications expose
numbers; they do not push each measurement to Prometheus.

**27. Why use exporters?**  
node_exporter exposes VM CPU, memory, disk and network counters.
blackbox_exporter makes HTTP and TCP probes. Neither requires adding host checks
to the trading code.

**28. What does `up` mean?**  
Prometheus successfully scraped that target. It does not prove every business
operation worked. That is why this lab also checks probes, prices and orders.

**29. How is `probe_success` different?**  
It is the result of an external HTTP/TCP check. A blackbox scrape can succeed
(`up=1`) while the target it probes fails (`probe_success=0`).

**30. Where do you use a counter?**  
`tradeops_orders_total{side="BUY"}` counts completed synthetic decisions.
Counters normally increase, but reset when the process restarts.

**31. Where do you use a gauge?**  
`tradeops_last_price{symbol="NIFTY"}` can rise or fall. The last successful fetch
timestamp is another gauge; subtract it from the current time to measure age.

**32. Why use a histogram for latency?**  
It counts observations in fixed buckets and exposes their sum and count.
This lets Prometheus estimate percentiles over a chosen time window without
saving every individual request.

**33. What exactly is this project's latency metric?**  
Elapsed time for one order-service feed-fetch cycle, including failed attempts.
It is not exchange execution latency, nor one observation per synthetic order.

**34. What does `rate(counter[1m])` do?**  
It estimates increase per second over one minute and handles observed resets.
Multiply orders per second by 60 to show orders per minute. Very short windows
are noisy and need enough scrape samples.

**35. How do you calculate p95 here?**  
`histogram_quantile(0.95, sum by (le, service)
(rate(tradeops_order_latency_seconds_bucket[1m])))`. Keep `le` because the
function needs the bucket boundaries. p95 is an estimate, not an exact request.

**36. Why does the slow-feed drill use 350 ms?**  
It exceeds the 300 ms alert threshold while normally staying below the
application's 400 ms rejection limit. Only `/prices` is delayed; `/health` and
`/metrics` remain responsive. Remove the root-owned flag to recover.

**37. What does an alert's `for:` mean?**  
Its expression must remain true continuously for that duration before firing.
HighOrderLatency waits two minutes. Scrape and evaluation timing add detection
delay, and the rate window must first reflect the fault.

**38. What are pending, firing and resolved?**  
Pending means the condition is true but has not lasted long enough. Firing means
the waiting period passed. Resolved means the condition stopped being active.
Prometheus's active-alert API drops resolved alerts; saved snapshots preserve
what was seen during the incident.

**39. Why group alerts in Alertmanager?**  
This project groups by alert name and service so related notifications can be
sent together. Severity routes use different repeat intervals.

**40. What does inhibition do?**  
A ServiceDown P1 suppresses smaller notifications for the same service and
environment. It does not stop Prometheus evaluating those rules or hide their
metrics. Check `inhibitedBy` in Alertmanager evidence; the real stop-feed drill
saved it in `docs/evidence/phase2/stop-feed/inhibition.json`.

**41. Why keep the Telegram token in a file?**  
It avoids embedding a secret in tracked configuration. The token, chat-ID file,
.env and generated receiver configuration are ignored by Git. Actual delivery
still requires valid credentials and a real test; validation alone is not proof.

**42. How do logs reach Grafana?**  
Alloy tails `/var/log/tradeops/*.log`, parses timestamps and levels, and sends
them to Loki. Grafana queries Loki. Position state and storage use named volumes.

**43. What is the difference between labels and text filtering in Loki?**  
`{job="tradeops",service="orders"}` selects indexed streams, then `|= "feed
unreachable"` filters their message text. Indexing every price or order ID would
create too many streams; keep labels bounded.

**44. How are Docker and the VM used differently?**  
Multipass provides a Linux VM with its own kernel. The monitoring containers
share that VM's kernel. The two Python applications run under systemd outside
those containers. This is not a Kubernetes project.

**45. Why are Docker volumes necessary?**  
They keep Prometheus, Loki, Grafana and Alloy state outside disposable container
filesystems. They survive ordinary container restarts. `docker compose down -v`
explicitly deletes named volumes, so it is not a routine restart command.

**46. Why use host networking here?**  
The application binds only to VM loopback. Linux host-network containers can
reach those listeners at 127.0.0.1. It also means whole-loopback network delay
can affect monitoring. This setup is for a trusted local lab; Mac Docker's
network behaviour is not the assumption here.

**47. What does Compose add?**  
One YAML file declares the seven pinned images, mounts, environment, networking,
restart policy and storage. `docker compose config` validates the model but
does not prove the services will start or connect; runtime checks do that.

**48. What does CI prove, and what does it miss?**  
It catches shell issues, Python lint failures, incorrect tested helper behaviour
and invalid monitoring config. The 39 Python cases cover random-walk prices,
order rules, alert formatting and handover parsing. Unit/config checks do not
prove real alert delivery, dashboard rendering or production reliability.

**49. How does your release rollback work?**  
Code is copied into a versioned directory, `current` is changed atomically, and
services restart. A health gate restores the previous release if the new one
fails. Three managed releases are retained, protecting current and previous.
Shared dependencies and database changes need separate rollback planning.

**50. Is this blue-green deployment, and how do you prove recovery?**  
No. Blue-green runs two environments and switches traffic. This single-instance
lab has restart downtime. I prove recovery with health endpoints, the Bash
check, cleared alerts and saved UTC evidence; a successful restart command alone
is insufficient.

### Reading the real incident timings

Prometheus `activeAt` is when the alert became active (including pending), not
necessarily when it first fired. Each Phase 2 timeline separately records the
fault start, first polling observation of firing in both systems, fix start,
first observation that both systems cleared the selected alert, and final Bash
health. Detection and resolution observations have polling uncertainty. A P3
recent-start rule intentionally remains active for ten minutes after restart;
the five-minute error window can also outlast the outage.
