"""feature/cli: every command, the --now option, seed, and report (STRETCH GOAL 2)."""

import csv
from datetime import timedelta
from pathlib import Path

import pytest

import db
import main
from claims import file_claim, report_counts

SEED_FILE = Path(__file__).resolve().parent.parent / "seed_claims.csv"


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "claims.db")


@pytest.fixture
def run(db_path, capsys):
    """Run `python main.py --db <tmp> ...` in-process; return (exit code, stdout, stderr)."""

    def _run(*args, now=None):
        argv = ["--db", db_path]
        if now is not None:
            argv += ["--now", now]
        code = main.main([*argv, *args])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return _run


def file_gold(run, passenger="Ada Lee", now="2026-11-02T10:00:00"):
    return run(
        "file", "--passenger", passenger, "--flight", "OA101", "--type", "lost",
        "--tier", "gold", now=now,
    )


def test_file_uses_now_for_filed_time_and_deadline(run):
    code, out, _ = file_gold(run)

    assert code == 0
    assert "Filed claim 1" in out
    assert "deadline 2026-11-02T14:00:00" in out


def test_file_with_bad_tier_prints_clear_error(run):
    code, out, err = run(
        "file", "--passenger", "Ada Lee", "--flight", "OA101", "--type", "lost",
        "--tier", "platinum", now="2026-11-02T10:00:00",
    )

    assert code == 1
    assert out == ""
    assert err.startswith("Error:")
    assert "tier" in err


def test_list_filters_by_status_and_tier(run):
    file_gold(run, "Ada Lee")
    run(
        "file", "--passenger", "Ben Ortiz", "--flight", "OA202", "--type", "delayed",
        "--tier", "silver", now="2026-11-02T10:00:00",
    )
    run("assign", "1", "--agent", "Dana", now="2026-11-02T10:05:00")

    _, assigned, _ = run("list", "--status", "assigned")
    _, silver, _ = run("list", "--tier", "silver")

    assert "Ada Lee" in assigned and "Ben Ortiz" not in assigned
    assert "Ben Ortiz" in silver and "Ada Lee" not in silver


def test_assign_resolve_and_close_from_the_command_line(run, db_path):
    file_gold(run)

    assert run("assign", "1", "--agent", "Dana", now="2026-11-02T10:05:00")[0] == 0
    assert run("resolve", "1", now="2026-11-02T10:10:00")[0] == 0
    code, out, _ = run("close", "1", now="2026-11-02T10:15:00")

    assert code == 0
    assert "closed" in out
    conn = db.connect(db_path)
    row = conn.execute("SELECT status, agent FROM claims WHERE id = 1").fetchone()
    assert tuple(row) == ("closed", "Dana")
    conn.close()


def test_escalate_with_now_past_deadline_prints_escalated_ids(run):
    file_gold(run, "Ada Lee")
    file_gold(run, "Ben Ortiz")

    code, out, _ = run("escalate", now="2026-11-02T14:01:00")

    assert code == 0
    assert "Escalated 2 claim(s): 1, 2" in out


def test_escalate_with_nothing_overdue_says_so(run):
    file_gold(run)

    code, out, _ = run("escalate", now="2026-11-02T14:00:00")

    assert code == 0
    assert "No claims are overdue" in out


def test_history_prints_every_entry_for_a_claim(run):
    file_gold(run)
    run("assign", "1", "--agent", "Dana", "--by", "Kim", now="2026-11-02T10:05:00")

    code, out, _ = run("history", "1")

    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 2
    assert "2026-11-02T10:00:00" in lines[0] and "open" in lines[0]
    assert "open -> assigned" in lines[1] and "Kim" in lines[1]


def test_seed_loads_every_row_of_seed_claims_csv(run, db_path):
    with SEED_FILE.open(newline="") as handle:
        expected = len(list(csv.DictReader(handle)))

    code, out, _ = run("seed", str(SEED_FILE), now="2026-11-02T10:00:00")

    assert code == 0
    assert f"Loaded {expected} claims" in out
    conn = db.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == expected
    conn.close()


def test_seed_with_missing_file_prints_clear_error(run, tmp_path):
    code, _, err = run("seed", str(tmp_path / "nope.csv"))

    assert code == 1
    assert err.startswith("Error:")
    assert "nope.csv" in err


def test_invalid_now_prints_clear_error(run):
    code, _, err = run("list", now="yesterday-ish")

    assert code == 1
    assert err.startswith("Error:")
    assert "--now" in err


def test_report_counts_open_and_overdue_by_tier(conn, now):
    file_claim(conn, "Ada Lee", "OA101", "lost", "gold", now=now)
    file_claim(conn, "Ben Ortiz", "OA202", "lost", "gold", now=now + timedelta(hours=3))
    file_claim(conn, "Cy Park", "OA303", "delayed", "silver", now=now)

    counts = report_counts(conn, now=now + timedelta(hours=4, minutes=1))

    assert counts["gold"] == {"open": 2, "overdue": 1}
    assert counts["silver"] == {"open": 1, "overdue": 0}
    assert counts["standard"] == {"open": 0, "overdue": 0}


def test_report_command_prints_counts_per_tier(run):
    file_gold(run, "Ada Lee")

    code, out, _ = run("report", now="2026-11-02T14:01:00")

    assert code == 0
    gold_line = next(line for line in out.splitlines() if line.startswith("gold"))
    assert gold_line.split() == ["gold", "1", "1"]
