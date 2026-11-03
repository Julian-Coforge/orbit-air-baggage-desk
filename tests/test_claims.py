"""feature/schema-and-filing: tables, filing, validation, deadlines, list."""

import sqlite3

import pytest

from claims import ClaimError, file_claim, get_claim, list_claims


def count_rows(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_file_valid_claim_is_stored_as_open(conn, now):
    claim_id = file_claim(
        conn, "Ada Lee", "OA101", "lost", "gold", note="Blue suitcase", now=now, changed_by="desk"
    )

    claim = get_claim(conn, claim_id)
    assert claim["passenger"] == "Ada Lee"
    assert claim["flight"] == "OA101"
    assert claim["type"] == "lost"
    assert claim["tier"] == "gold"
    assert claim["status"] == "open"
    assert claim["agent"] is None
    assert claim["note"] == "Blue suitcase"
    assert claim["filed_at"] == "2026-11-02T10:00:00"


def test_blank_passenger_is_rejected(conn, now):
    with pytest.raises(ClaimError, match="passenger"):
        file_claim(conn, "   ", "OA101", "lost", "gold", now=now)
    assert count_rows(conn, "claims") == 0
    assert count_rows(conn, "history") == 0


def test_blank_flight_is_rejected(conn, now):
    with pytest.raises(ClaimError, match="flight"):
        file_claim(conn, "Ada Lee", "", "lost", "gold", now=now)
    assert count_rows(conn, "claims") == 0
    assert count_rows(conn, "history") == 0


def test_unknown_type_is_rejected(conn, now):
    with pytest.raises(ClaimError, match="type"):
        file_claim(conn, "Ada Lee", "OA101", "stolen", "gold", now=now)
    assert count_rows(conn, "claims") == 0
    assert count_rows(conn, "history") == 0


def test_unknown_tier_is_rejected(conn, now):
    with pytest.raises(ClaimError, match="tier"):
        file_claim(conn, "Ada Lee", "OA101", "lost", "platinum", now=now)
    assert count_rows(conn, "claims") == 0
    assert count_rows(conn, "history") == 0


def test_gold_deadline_is_4_hours_after_filing(conn, now):
    claim_id = file_claim(conn, "Ada Lee", "OA101", "lost", "gold", now=now)
    assert get_claim(conn, claim_id)["deadline"] == "2026-11-02T14:00:00"


def test_silver_deadline_is_24_hours_after_filing(conn, now):
    claim_id = file_claim(conn, "Ada Lee", "OA101", "lost", "silver", now=now)
    assert get_claim(conn, claim_id)["deadline"] == "2026-11-03T10:00:00"


def test_standard_deadline_is_72_hours_after_filing(conn, now):
    claim_id = file_claim(conn, "Ada Lee", "OA101", "lost", "standard", now=now)
    assert get_claim(conn, claim_id)["deadline"] == "2026-11-05T10:00:00"


def test_filing_writes_first_history_entry(conn, now):
    claim_id = file_claim(conn, "Ada Lee", "OA101", "lost", "gold", now=now, changed_by="Sam")

    rows = conn.execute(
        "SELECT claim_id, old_status, new_status, changed_by, changed_at FROM history"
    ).fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["claim_id"] == claim_id
    assert row["old_status"] is None
    assert row["new_status"] == "open"
    assert row["changed_by"] == "Sam"
    assert row["changed_at"] == "2026-11-02T10:00:00"


def test_list_filters_by_status_and_tier(conn, now):
    gold = file_claim(conn, "Ada Lee", "OA101", "lost", "gold", now=now)
    silver = file_claim(conn, "Ben Ortiz", "OA202", "delayed", "silver", now=now)
    gold_resolved = file_claim(conn, "Cy Park", "OA303", "damaged", "gold", now=now)
    conn.execute("UPDATE claims SET status = 'resolved' WHERE id = ?", (gold_resolved,))

    def ids(rows):
        return [row["id"] for row in rows]

    assert ids(list_claims(conn)) == [gold, silver, gold_resolved]
    assert ids(list_claims(conn, status="open")) == [gold, silver]
    assert ids(list_claims(conn, tier="gold")) == [gold, gold_resolved]
    assert ids(list_claims(conn, status="open", tier="gold")) == [gold]


def test_database_check_constraints_reject_bad_values(conn):
    insert = (
        "INSERT INTO claims (passenger, flight, type, tier, status, note, filed_at, deadline) "
        "VALUES ('Ada Lee', 'OA101', ?, ?, ?, '', '2026-11-02T10:00:00', '2026-11-02T14:00:00')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, ("stolen", "gold", "open"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, ("lost", "platinum", "open"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, ("lost", "gold", "lost-forever"))
