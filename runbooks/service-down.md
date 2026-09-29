# Service down or repeated crashes

Run these commands inside `multipass shell tradeops`.

## Symptoms
Feed unavailable, order errors, or restart counter increasing.

## Alert that fires
P1 service-feed / service-orders; P2 restart-feed / restart-orders or error-rate

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
