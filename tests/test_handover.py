import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.handover_report import parse_alert_line, recent_lines

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("severity", ["P1", "P2", "P3"])
def test_real_bash_formatter_round_trips_into_handover(severity):
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; format_alert_line "$2" "$3" "$4" "$5" "$6"',
            "--",
            str(ROOT / "scripts/alert_format.sh"),
            "2026-09-29T12:00:00Z",
            severity,
            "http-9001",
            "health endpoint failed",
            "runbooks/port-blocked.md",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    fields = parse_alert_line(result.stdout)
    assert fields == [
        "2026-09-29T12:00:00Z",
        severity,
        "http-9001",
        "health endpoint failed",
        "runbooks/port-blocked.md",
    ]
    assert result.stdout.count(" | ") == 4
    assert result.stdout.endswith("\n")


@pytest.mark.parametrize(
    "line",
    [
        "",
        "broken",
        "2026-09-29T12:00:00Z | P0 | check | detail | runbook",
        "2026-02-30T12:00:00Z | P1 | check | detail | runbook",
        "2026-09-29T12:00:00Z | P1 | check | detail | runbook | extra",
    ],
)
def test_malformed_alert_is_rejected(line):
    assert parse_alert_line(line) is None


def test_shift_window_excludes_old_future_and_malformed_lines(tmp_path):
    (tmp_path / "orders.log").write_text(
        "2026-09-29T12:00:00Z | ERROR | end\n2026-09-29T12:00:01Z | ERROR | future\ninvalid line\n"
    )
    (tmp_path / "orders.log.1").write_text(
        "2026-09-29T10:00:00Z | ERROR | start\n2026-09-29T09:59:59Z | ERROR | too old\n"
    )
    lines = list(
        recent_lines(
            tmp_path,
            "orders.log*",
            datetime(2026, 9, 29, 10, tzinfo=timezone.utc),
            datetime(2026, 9, 29, 12, tzinfo=timezone.utc),
        )
    )
    assert len(lines) == 2
    assert {line.rsplit(" | ", 1)[1] for line in lines} == {"start", "end"}


def test_formatter_rejects_ambiguous_fields():
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; format_alert_line now P1 check "bad|field" runbook',
            "--",
            str(ROOT / "scripts/alert_format.sh"),
        ]
    )
    assert result.returncode == 2
