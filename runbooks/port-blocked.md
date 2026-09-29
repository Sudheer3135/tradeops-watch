# Port blocked or feed slow

Run these commands inside `multipass shell tradeops`.

## Symptoms
TCP health checks fail, or order service reports a degraded feed.

## Alert that fires
HealthProbeFailed P1 and possibly ServiceDown P1 for a blocked feed port. A 350 ms slow-feed drill keeps health responsive but triggers HighOrderLatency P2 after two minutes above 300 ms p95. Whole-loopback netem delay can also degrade monitoring requests.

## What you see in Grafana
Compare HTTP/TCP probes with application scrape status. Trading p95/p99 rises for slow fetches; successful feed responses can still be slow. Alerts shows HighOrderLatency after its waiting period. For network faults, look for feed errors in Logs; the controlled 350 ms delay normally stays below the application’s 400 ms rejection threshold, so an empty ERROR panel is expected.

## LogQL query to use
Set Explore’s time range to the incident UTC window.
```logql
{job="tradeops",service="orders"} | regexp `latency_ms=(?P<ms>[0-9.]+)` | ms > 300
```

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
sudo /opt/tradeops/scripts/chaos.sh fix-slow-feed
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
