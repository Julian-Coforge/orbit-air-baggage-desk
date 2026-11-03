"""feature/assign-and-status: assign, resolve, close, allowed changes, history."""

from datetime import timedelta

import pytest

from claims import (
    ClaimError,
    assign_claim,
    close_claim,
    file_claim,
    get_claim,
    get_history,
    resolve_claim,
)


def new_claim(conn, now):
    return file_claim(conn, "Ada Lee", "OA101", "lost", "gold", now=now)


def force_status(conn, claim_id, status):
    """Put a claim straight into a status this branch has no command for yet."""
    conn.execute("UPDATE claims SET status = ? WHERE id = ?", (status, claim_id))


def test_assign_open_claim(conn, now):
    claim_id = new_claim(conn, now)

    assign_claim(conn, claim_id, "Dana", now=now)

    claim = get_claim(conn, claim_id)
    assert claim["status"] == "assigned"
    assert claim["agent"] == "Dana"


def test_assign_escalated_claim(conn, now):
    claim_id = new_claim(conn, now)
    force_status(conn, claim_id, "escalated")

    assign_claim(conn, claim_id, "Priya", now=now)

    claim = get_claim(conn, claim_id)
    assert claim["status"] == "assigned"
    assert claim["agent"] == "Priya"


def test_resolve_assigned_claim(conn, now):
    claim_id = new_claim(conn, now)
    assign_claim(conn, claim_id, "Dana", now=now)

    resolve_claim(conn, claim_id, now=now)

    assert get_claim(conn, claim_id)["status"] == "resolved"


def test_resolve_escalated_claim(conn, now):
    claim_id = new_claim(conn, now)
    force_status(conn, claim_id, "escalated")

    resolve_claim(conn, claim_id, now=now)

    assert get_claim(conn, claim_id)["status"] == "resolved"


def test_close_resolved_claim(conn, now):
    claim_id = new_claim(conn, now)
    assign_claim(conn, claim_id, "Dana", now=now)
    resolve_claim(conn, claim_id, now=now)

    close_claim(conn, claim_id, now=now)

    assert get_claim(conn, claim_id)["status"] == "closed"


def test_closing_open_claim_is_rejected(conn, now):
    claim_id = new_claim(conn, now)

    with pytest.raises(ClaimError, match="from open to closed"):
        close_claim(conn, claim_id, now=now)

    assert get_claim(conn, claim_id)["status"] == "open"
    assert len(get_history(conn, claim_id)) == 1


def test_resolving_open_claim_is_rejected(conn, now):
    claim_id = new_claim(conn, now)

    with pytest.raises(ClaimError, match="from open to resolved"):
        resolve_claim(conn, claim_id, now=now)

    assert get_claim(conn, claim_id)["status"] == "open"


def test_assigning_closed_claim_is_rejected(conn, now):
    claim_id = new_claim(conn, now)
    force_status(conn, claim_id, "closed")

    with pytest.raises(ClaimError, match="from closed to assigned"):
        assign_claim(conn, claim_id, "Dana", now=now)

    claim = get_claim(conn, claim_id)
    assert claim["status"] == "closed"
    assert claim["agent"] is None


def test_assigning_blank_agent_is_rejected(conn, now):
    claim_id = new_claim(conn, now)

    with pytest.raises(ClaimError, match="agent"):
        assign_claim(conn, claim_id, "   ", now=now)

    assert get_claim(conn, claim_id)["status"] == "open"


def test_unknown_claim_id_is_rejected(conn, now):
    with pytest.raises(ClaimError, match="does not exist"):
        assign_claim(conn, 999, "Dana", now=now)
    with pytest.raises(ClaimError, match="does not exist"):
        resolve_claim(conn, 999, now=now)
    with pytest.raises(ClaimError, match="does not exist"):
        close_claim(conn, 999, now=now)


def test_each_status_change_adds_complete_history_entry(conn, now):
    claim_id = new_claim(conn, now)
    later = now + timedelta(hours=1)

    assign_claim(conn, claim_id, "Dana", now=later, changed_by="Supervisor Kim")

    entry = get_history(conn, claim_id)[-1]
    assert entry["claim_id"] == claim_id
    assert entry["old_status"] == "open"
    assert entry["new_status"] == "assigned"
    assert entry["changed_by"] == "Supervisor Kim"
    assert entry["changed_at"] == "2026-11-02T11:00:00"


def test_full_life_of_a_claim_is_in_history_in_order(conn, now):
    claim_id = new_claim(conn, now)
    assign_claim(conn, claim_id, "Dana", now=now + timedelta(minutes=10))
    resolve_claim(conn, claim_id, now=now + timedelta(minutes=20))
    close_claim(conn, claim_id, now=now + timedelta(minutes=30))

    history = get_history(conn, claim_id)
    assert [(h["old_status"], h["new_status"]) for h in history] == [
        (None, "open"),
        ("open", "assigned"),
        ("assigned", "resolved"),
        ("resolved", "closed"),
    ]
    assert [h["changed_at"] for h in history] == [
        "2026-11-02T10:00:00",
        "2026-11-02T10:10:00",
        "2026-11-02T10:20:00",
        "2026-11-02T10:30:00",
    ]
