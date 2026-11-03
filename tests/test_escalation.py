"""feature/deadlines-and-escalation: overdue rule, escalation, history, rollback."""

import sqlite3
from datetime import timedelta

import pytest

from claims import (
    ClaimError,
    assign_claim,
    close_claim,
    escalate_claim,
    escalate_overdue,
    file_claim,
    get_claim,
    get_history,
    is_overdue,
    resolve_claim,
)

# A gold claim filed at NOW (10:00) has its deadline at 14:00.
ONE_MINUTE = timedelta(minutes=1)


def gold_claim(conn, now, passenger="Ada Lee"):
    return file_claim(conn, passenger, "OA101", "lost", "gold", now=now)


def deadline_of(conn, claim_id):
    return get_claim(conn, claim_id)["deadline"]


def test_one_minute_before_deadline_is_not_overdue(conn, now):
    claim_id = gold_claim(conn, now)
    at_1359 = now + timedelta(hours=4) - ONE_MINUTE
    assert is_overdue(deadline_of(conn, claim_id), at_1359) is False


def test_exactly_at_deadline_is_not_overdue(conn, now):
    claim_id = gold_claim(conn, now)
    at_1400 = now + timedelta(hours=4)
    assert is_overdue(deadline_of(conn, claim_id), at_1400) is False


def test_one_minute_after_deadline_is_overdue(conn, now):
    claim_id = gold_claim(conn, now)
    at_1401 = now + timedelta(hours=4) + ONE_MINUTE
    assert is_overdue(deadline_of(conn, claim_id), at_1401) is True


def test_overdue_open_claim_is_escalated(conn, now):
    claim_id = gold_claim(conn, now)

    escalate_overdue(conn, now=now + timedelta(hours=4) + ONE_MINUTE)

    assert get_claim(conn, claim_id)["status"] == "escalated"


def test_overdue_assigned_claim_is_escalated(conn, now):
    claim_id = gold_claim(conn, now)
    assign_claim(conn, claim_id, "Dana", now=now)

    escalate_overdue(conn, now=now + timedelta(hours=4) + ONE_MINUTE)

    assert get_claim(conn, claim_id)["status"] == "escalated"


def test_claim_not_yet_overdue_is_left_alone(conn, now):
    claim_id = gold_claim(conn, now)

    escalated = escalate_overdue(conn, now=now + timedelta(hours=4))

    assert escalated == []
    assert get_claim(conn, claim_id)["status"] == "open"


def test_resolved_and_closed_claims_are_left_alone(conn, now):
    resolved_id = gold_claim(conn, now, "Ada Lee")
    assign_claim(conn, resolved_id, "Dana", now=now)
    resolve_claim(conn, resolved_id, now=now)
    closed_id = gold_claim(conn, now, "Ben Ortiz")
    assign_claim(conn, closed_id, "Dana", now=now)
    resolve_claim(conn, closed_id, now=now)
    close_claim(conn, closed_id, now=now)

    escalated = escalate_overdue(conn, now=now + timedelta(days=10))

    assert escalated == []
    assert get_claim(conn, resolved_id)["status"] == "resolved"
    assert get_claim(conn, closed_id)["status"] == "closed"


def test_escalated_claim_is_not_escalated_again(conn, now):
    claim_id = gold_claim(conn, now)
    escalate_overdue(conn, now=now + timedelta(hours=5))
    history_before = len(get_history(conn, claim_id))

    escalated = escalate_overdue(conn, now=now + timedelta(hours=6))

    assert escalated == []
    assert get_claim(conn, claim_id)["status"] == "escalated"
    assert len(get_history(conn, claim_id)) == history_before


def test_escalating_a_claim_that_is_not_overdue_is_rejected(conn, now):
    claim_id = gold_claim(conn, now)

    with pytest.raises(ClaimError, match="not overdue"):
        escalate_claim(conn, claim_id, now=now + timedelta(hours=4))

    assert get_claim(conn, claim_id)["status"] == "open"
    assert len(get_history(conn, claim_id)) == 1


def test_escalate_overdue_returns_the_escalated_ids_in_order(conn, now):
    first = gold_claim(conn, now, "Ada Lee")
    on_time = file_claim(conn, "Ben Ortiz", "OA202", "delayed", "silver", now=now)
    second = gold_claim(conn, now, "Cy Park")
    assign_claim(conn, second, "Dana", now=now)

    escalated = escalate_overdue(conn, now=now + timedelta(hours=5))

    assert escalated == [first, second]
    assert get_claim(conn, on_time)["status"] == "open"


def test_escalation_adds_history_entry_by_system(conn, now):
    open_id = gold_claim(conn, now, "Ada Lee")
    assigned_id = gold_claim(conn, now, "Ben Ortiz")
    assign_claim(conn, assigned_id, "Dana", now=now)
    later = now + timedelta(hours=4) + ONE_MINUTE

    escalate_overdue(conn, now=later)

    for claim_id, old_status in [(open_id, "open"), (assigned_id, "assigned")]:
        entry = get_history(conn, claim_id)[-1]
        assert entry["old_status"] == old_status
        assert entry["new_status"] == "escalated"
        assert entry["changed_by"] == "system"
        assert entry["changed_at"] == "2026-11-02T14:01:00"


def test_failed_history_write_rolls_back_the_claim_change(conn, now):
    claim_id = gold_claim(conn, now)
    conn.execute(
        "CREATE TEMP TRIGGER fail_history BEFORE INSERT ON history "
        "BEGIN SELECT RAISE(ABORT, 'forced history failure'); END;"
    )
    try:
        with pytest.raises(sqlite3.IntegrityError, match="forced history failure"):
            assign_claim(conn, claim_id, "Dana", now=now, changed_by="test")

        claim = get_claim(conn, claim_id)
        assert claim["status"] == "open"
        assert claim["agent"] is None
        assert len(get_history(conn, claim_id)) == 1
    finally:
        conn.execute("DROP TRIGGER IF EXISTS fail_history")
