# Service down or repeated crashes

Run these commands inside `multipass shell tradeops`.

## Symptoms
Feed unavailable, order errors, or restart counter increasing.

## Alert that fires
ServiceDown P1, HealthProbeFailed P1, FeedErrorsHigh P2 and ServiceRestartedRecently P3. A five-second crash may recover before the P1 waiting period; use the recent-start P3 and systemd journal for that drill.

## What you see in Grafana
Service health shows scrape/probe status and process age. Trading shows interrupted price/order rates and feed errors. Alerts lists current firing rules; Logs contains order fetch failures. A stopped process cannot emit its own final log, so also inspect journald.

## LogQL query to use
Set Explore’s time range to the incident UTC window.
```logql
{job="tradeops",service="orders"} |= "feed unreachable"
```

## Step-by-step checks
Run in order; save output before changing anything.
```bash
systemctl status tradeops-feed tradeops-orders --no-pager
journalctl -u tradeops-feed -u tradeops-orders --since '10 minutes ago' --no-pager
ss -tulpn
sudo /opt/tradeops/scripts/log_search.sh errors 5
ps -eo pid,user,stat,pcpu,pmem,args --sort=-pcpu | head
```

## Fix
```bash
sudo /opt/tradeops/scripts/chaos.sh fix-feed
# For a real crash, inspect the journal first and fix the cause before restarting.
sudo systemctl start tradeops-orders
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
