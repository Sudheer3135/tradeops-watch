# TOW-002: Feed deliberately stopped; orders stayed running and reported dependency failure

- **ID:** TOW-002
- **Date/time (UTC):** 2026-09-29T11:17:52Z to 2026-09-29T11:18:04Z
- **Severity:** P1 (lab policy)
- **Summary:** Feed deliberately stopped; orders stayed running and reported dependency failure. Impact was limited to this synthetic single-VM lab.
- **Detection:** Healthcheck returned 2 at 2026-09-29T11:17:58Z. Its actual active checks were:

```text
P1|service-feed|service inactive
P1|port-9001|port not listening
P1|http-9001|health endpoint failed or degraded
P1|http-9002|health endpoint failed or degraded
```

Notifications for repeated checks may be suppressed for ten minutes; the active
state and exit status above still record detection. See the raw output for
which new notification lines were written.

## Timeline (UTC)

| Time | Observed action/result |
|---|---|
| 2026-09-29T11:17:52Z | Injected `stop-feed` |
| 2026-09-29T11:17:58Z | Healthcheck detected the failure (exit 2) |
| 2026-09-29T11:17:58Z | Ran the documented fix |
| 2026-09-29T11:18:04Z | Healthcheck exit 0 and both HTTP endpoints healthy; scenario PASS |

## Root cause
The drill ran systemctl stop tradeops-feed. The feed remained inactive while the order process kept retrying.

## Fix
Followed [service-down runbook](../runbooks/service-down.md). fix-feed started the stopped service.

## Verification
Actual final monitoring line:

```text
2026-09-29T11:18:03Z | healthcheck exit=0 CPU=0% memory=13% disk=24% errors=5
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
An intentional stop is different from a crash. Restart=on-failure does not undo an intentional stop.

## Evidence
[Complete unedited scenario output](../docs/evidence/stop-feed.txt).
