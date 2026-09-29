# Disk usage high

Run these commands inside `multipass shell tradeops`.

## Symptoms
Root filesystem exceeds 85%; writes may fail if it grows further.

## Alert that fires
P2 disk

## Step-by-step checks
Run in order; save output before changing anything.
```bash
df -h /
sudo du -sh /var/log/tradeops /var/lib/tradeops
sudo du -xhd1 /var | sort -h
sudo journalctl --disk-usage
```

## Fix
```bash
sudo /opt/tradeops/scripts/chaos.sh fix-disk
# Remove only the known lab file. Never blindly delete production logs.
sudo logrotate -d /etc/logrotate.d/tradeops
df -h /
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
