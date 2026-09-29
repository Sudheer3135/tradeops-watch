# How to read the test evidence

This project uses an actual Multipass Ubuntu VM. Application prices/orders are
fictional, but all saved command output and incidents are from real local runs.

The main integration runner is `scripts/verify_lab.sh`. Each scenario records:

1. UTC start time and the actual fault command output.
2. A health check with a nonzero exit code and current alert state.
3. Diagnostic output from the relevant runbook.
4. The actual repair and its UTC timestamp.
5. Repeated health checks until exit 0, two healthy HTTP responses, and PASS.

The runner invokes the exact check used by cron. It does not wait for cron's
minute boundary to detect short failures. `cron.txt` separately records that
cron really invokes monitoring. A warning can persist after HTTP recovery
because errors are counted over the trailing five minutes. Those waiting
periods remain visible in the evidence; no error records are cleared to force
success. Repeated P1 notifications during later drills can be suppressed by
the ten-minute cooldown, while the active alert state and exit code still
show the problem.

`verify_monitor.sh` uses a memory threshold of zero to test warning detection
and notification deduplication safely. This is a **threshold-override test**,
not a claim that the VM actually ran out of memory. CPU, disk, stopped/crashed
services, firewall rejection, and loopback delay are real injected faults.

`http-api.txt` checks JSON response types, all five positive prices, changes
over time, increasing order counts, health responses, and unknown-route 404s.
`macos-safety-guard.txt` records the expected refusal on the host.
`service-configuration.txt` records the service account, restart policy,
hardening settings, listeners, and a dry-run validation of logrotate config.

## Setup issues found and fixed

- The mounted Mac Desktop directory could not be read by Multipass:
  `mount-permission-failure.txt`. A source archive transferred directly into
  Ubuntu worked; README documents this tested fallback.
- Python compilation created `scripts/__pycache__`; the installer's original
  broad wildcard tried copying that directory: `install-first-attempt.txt`.
  The installer now selects `.sh` and `.py` files explicitly.
- `install.txt` and `install-rerun.txt` preserve the successful runs after that
  fix. `syntax.txt` is the final syntax/compilation result inside Ubuntu.

## Limits

Telegram is skipped because credentials were not supplied; delivery is not
claimed as verified. No production system, exchange, or broker was contacted.
P1/P2 policy and escalation roles are lab conventions. Service log rotation
uses the Python standard library; this run validates configuration rather than
claiming a long-duration retention or performance test. Systemd's journal may
show IST while application logs and test markers use UTC (IST = UTC + 05:30).
