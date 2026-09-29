# TOW-004: Two CPU workers drove aggregate CPU to 100%

- **ID:** TOW-004
- **Date/time (UTC):** 2026-09-29T11:18:15Z to 2026-09-29T11:18:26Z
- **Severity:** P2 (lab policy)
- **Summary:** Two CPU workers drove aggregate CPU to 100%. Impact was limited to this synthetic single-VM lab.
- **Detection:** Healthcheck returned 1 at 2026-09-29T11:18:21Z. Its actual active checks were:

```text
P2|cpu|CPU 100% >= 85%
```

Notifications for repeated checks may be suppressed for ten minutes; the active
state and exit status above still record detection. See the raw output for
which new notification lines were written.

## Timeline (UTC)

| Time | Observed action/result |
|---|---|
| 2026-09-29T11:18:15Z | Injected `cpu-spike` |
| 2026-09-29T11:18:21Z | Healthcheck detected the failure (exit 1) |
| 2026-09-29T11:18:21Z | Ran the documented fix |
| 2026-09-29T11:18:26Z | Healthcheck exit 0 and both HTTP endpoints healthy; scenario PASS |

## Root cause
The bounded lab CPU unit started one yes worker per vCPU. ps showed both workers using approximately one CPU each.

## Fix
Followed [high-cpu runbook](../runbooks/high-cpu.md). fix-cpu stopped the temporary systemd unit; measured CPU returned to 0%.

## Verification
Actual final monitoring line:

```text
2026-09-29T11:18:26Z | healthcheck exit=0 CPU=0% memory=14% disk=24% errors=5
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
Identify the process before stopping it. Group worker processes in a managed unit so cleanup removes all children.

## Evidence
[Complete unedited scenario output](../docs/evidence/cpu-spike.txt).
