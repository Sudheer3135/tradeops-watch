# TOW-001: Feed process killed; systemd recovered it automatically

- **ID:** TOW-001
- **Date/time (UTC):** 2026-09-29T11:17:23Z to 2026-09-29T11:17:52Z
- **Severity:** P1 (lab policy)
- **Summary:** Feed process killed; systemd recovered it automatically. Impact was limited to this synthetic single-VM lab.
- **Detection:** Healthcheck returned 2 at 2026-09-29T11:17:25Z. Its actual active checks were:

```text
P1|service-feed|service inactive
P1|port-9001|port not listening
P1|http-9001|health endpoint failed or degraded
```

Notifications for repeated checks may be suppressed for ten minutes; the active
state and exit status above still record detection. See the raw output for
which new notification lines were written.

## Timeline (UTC)

| Time | Observed action/result |
|---|---|
| 2026-09-29T11:17:23Z | Injected `kill-feed` |
| 2026-09-29T11:17:25Z | Healthcheck detected the failure (exit 2) |
| 2026-09-29T11:17:31Z | Ran the documented fix |
| 2026-09-29T11:17:52Z | Healthcheck exit 0 and both HTTP endpoints healthy; scenario PASS |

## Root cause
SIGKILL was deliberately sent to the feed MainPID. systemd recorded status=9/KILL and restarted it at 11:17:28 UTC.

## Fix
Followed [service-down runbook](../runbooks/service-down.md). Automatic systemd recovery was verified before the explicit fix-feed command.

## Verification
Actual final monitoring line:

```text
2026-09-29T11:17:52Z | healthcheck exit=0 CPU=0% memory=14% disk=24% errors=2
```

The evidence also contains both successful JSON health responses and the PASS
marker. Any interval with a residual warning is preserved in the raw output.

## Escalation needed
No: this was a controlled isolated lab drill and recovery succeeded. For a real
trading outage, escalate P1 immediately to the on-call DevOps/SRE and application
owner; involve the network owner for unexplained firewall/latency problems.
For an unresolved P2, contact the on-call infrastructure owner. Include UTC
times, affected services, alert checks, logs, attempted fixes, and current impact.
No external message was sent during this test.

## Lessons learned
A crash restarts automatically; a brief outage may occur between cron checks. Use restart counters as well as HTTP checks.

## Evidence
[Complete unedited scenario output](../docs/evidence/kill-feed.txt).
