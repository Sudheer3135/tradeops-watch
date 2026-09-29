# TOW-006: Loopback delay made the feed too slow and HTTP checks fail

- **ID:** TOW-006
- **Date/time (UTC):** 2026-09-29T11:22:57Z to 2026-09-29T11:23:32Z
- **Severity:** P1 (lab policy)
- **Summary:** Loopback delay made the feed too slow and HTTP checks fail. Impact was limited to this synthetic single-VM lab.
- **Detection:** Healthcheck returned 2 at 2026-09-29T11:23:11Z. Its actual active checks were:

```text
P1|http-9001|health endpoint failed or degraded
P1|http-9002|health endpoint failed or degraded
P2|error-rate|7 errors in last 5 minutes > 5
```

Notifications for repeated checks may be suppressed for ten minutes; the active
state and exit status above still record detection. See the raw output for
which new notification lines were written.

## Timeline (UTC)

| Time | Observed action/result |
|---|---|
| 2026-09-29T11:22:57Z | Injected `net-delay` |
| 2026-09-29T11:23:11Z | Healthcheck detected the failure (exit 2) |
| 2026-09-29T11:23:11Z | Ran the documented fix |
| 2026-09-29T11:23:32Z | Healthcheck exit 0 and both HTTP endpoints healthy; scenario PASS |

## Root cause
tc netem added 500 ms per affected loopback packet. Full HTTP requests took roughly 2060–2175 ms, above the order service 400 ms limit.

## Fix
Followed [port-blocked runbook](../runbooks/port-blocked.md). fix-delay removed the lab-owned root qdisc. Both endpoints recovered; remaining error-window warnings aged out.

## Verification
Actual final monitoring line:

```text
2026-09-29T11:23:32Z | healthcheck exit=0 CPU=0% memory=14% disk=24% errors=5
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
A 500 ms packet delay can produce a multi-second HTTP transaction. Inspect tc and measure application latency rather than assuming packet delay equals request latency.

## Evidence
[Complete unedited scenario output](../docs/evidence/net-delay.txt).
