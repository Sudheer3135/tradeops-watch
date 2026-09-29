# TOW-003: Root filesystem reached 88% and triggered a disk warning

- **ID:** TOW-003
- **Date/time (UTC):** 2026-09-29T11:18:04Z to 2026-09-29T11:18:15Z
- **Severity:** P2 (lab policy)
- **Summary:** Root filesystem reached 88% and triggered a disk warning. Impact was limited to this synthetic single-VM lab.
- **Detection:** Healthcheck returned 1 at 2026-09-29T11:18:10Z. Its actual active checks were:

```text
P2|disk|Disk 88% >= 85%
```

Notifications for repeated checks may be suppressed for ten minutes; the active
state and exit status above still record detection. See the raw output for
which new notification lines were written.

## Timeline (UTC)

| Time | Observed action/result |
|---|---|
| 2026-09-29T11:18:04Z | Injected `fill-disk` |
| 2026-09-29T11:18:10Z | Healthcheck detected the failure (exit 1) |
| 2026-09-29T11:18:10Z | Ran the documented fix |
| 2026-09-29T11:18:15Z | Healthcheck exit 0 and both HTTP endpoints healthy; scenario PASS |

## Root cause
The drill allocated a known filler file under /var/lib/tradeops. df showed 88% used with 1.2 GiB available.

## Fix
Followed [disk-full runbook](../runbooks/disk-full.md). fix-disk removed only the lab filler; utilization returned to 24%.

## Verification
Actual final monitoring line:

```text
2026-09-29T11:18:15Z | healthcheck exit=0 CPU=0% memory=14% disk=24% errors=5
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
Use df to identify the filesystem and du to find growth. Keep a safety margin and delete only known disposable data.

## Evidence
[Complete unedited scenario output](../docs/evidence/fill-disk.txt).
