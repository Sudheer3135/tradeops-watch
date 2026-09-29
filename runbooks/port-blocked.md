# Port blocked or feed slow

Run these commands inside `multipass shell tradeops`.

## Symptoms
TCP health checks fail, or order service reports a degraded feed.

## Alert that fires
P1 port-9001 / port-9002 or http-9001 / http-9002; P2 error-rate

## Step-by-step checks
Run in order; save output before changing anything.
```bash
ss -tulpn
curl -v --max-time 2 http://127.0.0.1:9001/health
curl -v --max-time 2 http://127.0.0.1:9002/health
sudo iptables -L OUTPUT -n -v --line-numbers
tc qdisc show dev lo
sudo /opt/tradeops/scripts/log_search.sh errors 5
```

## Fix
```bash
sudo /opt/tradeops/scripts/chaos.sh fix-port
sudo /opt/tradeops/scripts/chaos.sh fix-delay
# Delete only the lab-owned rule/qdisc; do not flush the firewall.
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
