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
- `docs/architecture.md`: the VM, service, monitoring, and log relationships.
- `docs/evidence/*.txt`: raw command output proving what was run and observed.
- `README.md`: setup, demo, evidence, and planned future work.
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
