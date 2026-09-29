# TOW-005: Loopback feed traffic rejected despite a listening service

- **ID:** TOW-005
- **Date/time (UTC):** 2026-09-29T11:18:26Z to 2026-09-29T11:22:57Z
- **Severity:** P1 (lab policy)
- **Summary:** Loopback feed traffic rejected despite a listening service. Impact was limited to this synthetic single-VM lab.
- **Detection:** Healthcheck returned 2 at 2026-09-29T11:18:32Z. Its actual active checks were:

```text
P1|http-9001|health endpoint failed or degraded
P1|http-9002|health endpoint failed or degraded
P2|error-rate|8 errors in last 5 minutes > 5
```

Notifications for repeated checks may be suppressed for ten minutes; the active
state and exit status above still record detection. See the raw output for
which new notification lines were written.

## Timeline (UTC)

| Time | Observed action/result |
|---|---|
| 2026-09-29T11:18:26Z | Injected `block-port` |
| 2026-09-29T11:18:32Z | Healthcheck detected the failure (exit 2) |
| 2026-09-29T11:18:32Z | Ran the documented fix |
| 2026-09-29T11:22:57Z | Healthcheck exit 0 and both HTTP endpoints healthy; scenario PASS |

## Root cause
The tagged iptables OUTPUT rule rejected local TCP port 9001. ss still showed both listeners and rule counters showed matched packets.

## Fix
Followed [port-blocked runbook](../runbooks/port-blocked.md). fix-port removed the tagged rule. The health result then changed from critical to an error-rate warning, and later to healthy.

## Verification
Actual final monitoring line:

```text
2026-09-29T11:22:57Z | healthcheck exit=0 CPU=0% memory=14% disk=24% errors=4
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
A listening socket is not proof that traffic can reach it. Recent-error warnings intentionally outlive the immediate HTTP failure.

## Evidence
[Complete unedited scenario output](../docs/evidence/block-port.txt).
