# High CPU or memory

Run these commands inside `multipass shell tradeops`.

## Symptoms
CPU or memory exceeds 85%; requests may become slow.

## Alert that fires
HighCPU P2 after CPU remains above 85% for 30 seconds (using a one-minute rate). HighMemory P2 uses a two-minute waiting period; the chaos suite does not deliberately exhaust memory.

## What you see in Grafana
System CPU and load rise during the bounded CPU drill, then fall after the worker service stops. Alerts shows HighCPU. Memory uses MemAvailable, so cached memory is not automatically treated as pressure. Logs may have no application errors for a short CPU event; compare with the Bash monitor’s alerts.

## LogQL query to use
Set Explore’s time range to the incident UTC window.
```logql
{job="tradeops",service="alerts"} |= "cpu"
```

## Step-by-step checks
Run in order; save output before changing anything.
```bash
top -b -n 1 | head -25
ps -eo pid,ppid,user,stat,pcpu,pmem,args --sort=-pcpu | head -20
free -m
systemctl status tradeops-chaos-cpu --no-pager
```

## Fix
```bash
sudo /opt/tradeops/scripts/chaos.sh fix-cpu
# CPU drill also expires after 120 seconds. Inspect before killing real processes.
```

## How to verify
```bash
curl -fsS --max-time 2 http://127.0.0.1:9001/health
curl -fsS --max-time 2 http://127.0.0.1:9002/health
sudo /opt/tradeops/scripts/healthcheck.sh
```
Expect both endpoints healthy and healthcheck exit 0. Recent errors remain in
the five-minute window; wait for them to age out and run the check again.

## When and whom to escalate
Escalate immediately to the on-call DevOps/SRE owner if recovery fails, or if
this could affect live trading. Notify the application owner for repeated
application errors and the network owner for unexplained network rules.
In this isolated lab, those are role names, not actual contacts.
Include UTC start time, severity, business impact, commands and output,
recent changes, attempted fixes, current status, and next action/owner.
