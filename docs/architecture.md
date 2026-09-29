# Architecture

```text
MacBook M2: source code + Multipass
  |
  +-- Ubuntu 24.04 ARM64 VM: tradeops (2 CPUs, 2 GiB RAM, 10 GiB disk)
       |
       +-- systemd (user: tradeops)
       |    +-- market_feed.py :9001 /prices, /health
       |    +-- order_service.py :9002 /health
       |           | GET /prices every 2 seconds
       |           +------------------> market_feed.py
       |
       +-- /var/log/tradeops/ (UTC logs; Python rotates service logs)
       +-- cron every minute --> healthcheck.sh
       |                          +-- systemctl / ss / curl / /proc / df
       |                          +-- alerts.log + persistent alert state
       |                          +-- optional Telegram (credentials absent by default)
       +-- log_search.sh --> errors and latency summary
       +-- handover_report.py --> shift Markdown report
       +-- chaos.sh --> controlled failures --> runbooks --> recovery
```

Both HTTP servers bind to VM loopback. Execute curl inside the VM.
Prices and orders are fictional; no exchange, broker, or real money is involved.
`After=` orders startup; it does not mean the feed HTTP endpoint is ready.
The order worker retries failures independently and reports HTTP 503 while degraded.
`Wants=` starts the feed with orders but allows orders to stay up when feed stops.
Monitoring state is root-owned under `/var/lib/tradeops`. A lock prevents cron
and manual checks from changing it at the same time. Alert cooldown is per
check; active issues are refreshed even when notifications are suppressed.
Service files rotate at 2 MB with three backups each; logrotate manages the
Bash alert/cron logs separately to avoid two rotators on one file.
