#!/usr/bin/env python3
"""Render a shift summary from UTC logs and the latest monitoring snapshot."""

import argparse
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_alert_line(line):
    """Return the five documented alert fields, or None for malformed input."""
    fields = line.strip().split(" | ")
    if len(fields) != 5 or fields[1] not in {"P1", "P2", "P3"} or not all(fields):
        return None
    try:
        datetime.strptime(fields[0], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return fields


def recent_lines(logdir, pattern, start, end):
    """Read valid UTC lines inside an inclusive shift window, including rotations."""
    for path in sorted(logdir.glob(pattern)):
        if path.is_file():
            for line in path.read_text(errors="replace").splitlines():
                try:
                    timestamp = datetime.strptime(line[:20], "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    continue
                if start <= timestamp <= end:
                    yield line


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=8)
    args = parser.parse_args()
    if not 0 < args.hours < float("inf"):
        parser.error("--hours must be positive and finite")
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=args.hours)
    logdir = Path("/var/log/tradeops")

    def recent(pattern):
        return recent_lines(logdir, pattern, start, now)

    alerts = [
        parsed for line in recent("alerts.log*") if (parsed := parse_alert_line(line)) is not None
    ]
    lines = [
        "# TradeOps shift handover",
        "",
        f"Window (UTC): {start.isoformat()} to {now.isoformat()}",
        "",
        "## Services now",
    ]
    for service in ("tradeops-feed", "tradeops-orders"):
        result = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True)
        lines.append(f"- {service}: {result.stdout.strip()}")
    lines += ["", "## Alerts by severity"]
    for severity in ("P1", "P2", "P3"):
        counts = Counter(a[2] for a in alerts if a[1] == severity)
        lines.append(
            f"- {severity}: {sum(counts.values())} notifications; "
            + (", ".join(f"{k} ({v})" for k, v in counts.items()) or "none")
        )
    state = Path("/var/lib/tradeops/active-alerts")
    stamp = Path("/var/lib/tradeops/last-check")
    fresh = stamp.exists() and now.timestamp() - int(stamp.read_text()) < 180
    active = (
        [line.split("|", 2) for line in state.read_text().splitlines()] if state.exists() else []
    )
    lines += ["", "## Open issues (latest health check)"]
    if not fresh:
        lines.append(
            "- Monitoring snapshot is missing or older than 3 minutes; run healthcheck before judging recovery."
        )
    lines += [f"- {a[0]} {a[1]}: {a[2]}" for a in active] or ["- None in latest snapshot."]
    keys = {a[1] for a in active}
    resolved = sorted({a[2] for a in alerts} - keys) if fresh else []
    lines += [
        "",
        "## Resolved issues",
        *([f"- {key}: absent from latest check" for key in resolved] or ["- None confirmed."]),
    ]
    errors = Counter(
        line.split(" | ", 2)[-1]
        for pattern in ("market_feed.log*", "order_service.log*")
        for line in recent(pattern)
        if " | ERROR | " in line
    )
    lines += [
        "",
        "## Top errors",
        *([f"- {n} × {error}" for error, n in errors.most_common(5)] or ["- None."]),
        "",
        "## Notes for next shift",
        "- Confirm both HTTP health endpoints and review active alerts.",
        "- An error-rate alert may persist for 5 minutes after recovery.",
        "- Read incidents/ and record owner, next action, and escalation for any unresolved issue.",
        "",
    ]
    report = "\n".join(lines)
    path = logdir / now.strftime("handover-%Y%m%d-%H%M.md")
    path.write_text(report)
    print(report)
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
