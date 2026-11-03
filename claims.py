"""Claim rules: filing, validation, deadlines and listing.

No function here reads the clock. Anything that needs the current time takes
it as a `now` argument, so the caller (main.py or a test) decides what now is.
All times are stored as UTC text in TIME_FORMAT.
"""

import sqlite3
from datetime import UTC, datetime, timedelta

CLAIM_TYPES = ("delayed", "lost", "damaged")
TIERS = ("standard", "silver", "gold")
STATUSES = ("open", "assigned", "escalated", "resolved", "closed")

# Hours a claim has to get a response, by tier.
TIER_HOURS = {"gold": 4, "silver": 24, "standard": 72}

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class ClaimError(ValueError):
    """A claim rule was broken. The message is written to be shown to the user."""


def to_utc(moment: datetime) -> datetime:
    """Return `moment` in UTC. A time without a timezone is taken to be UTC already."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def format_time(moment: datetime) -> str:
    """Turn a datetime into the stored UTC text form, to the second."""
    return to_utc(moment).strftime(TIME_FORMAT)


def parse_time(text: str) -> datetime:
    """Turn stored UTC text back into a timezone-aware datetime."""
    return datetime.strptime(text, TIME_FORMAT).replace(tzinfo=UTC)


def deadline_for(tier: str, filed_at: datetime) -> datetime:
    """The response deadline for a claim of `tier` filed at `filed_at`."""
    return to_utc(filed_at) + timedelta(hours=TIER_HOURS[tier])


def _require_text(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise ClaimError(f"{field} cannot be blank")
    return value.strip()


def _require_choice(value: str, field: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ClaimError(f"unknown {field} {value!r}: must be one of {', '.join(choices)}")
    return value


def _add_history(
    conn: sqlite3.Connection,
    claim_id: int,
    old_status: str | None,
    new_status: str,
    changed_by: str,
    now: datetime,
) -> None:
    conn.execute(
        "INSERT INTO history (claim_id, old_status, new_status, changed_by, changed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (claim_id, old_status, new_status, changed_by, format_time(now)),
    )


def file_claim(
    conn: sqlite3.Connection,
    passenger: str,
    flight: str,
    claim_type: str,
    tier: str,
    note: str = "",
    *,
    now: datetime,
    changed_by: str = "desk",
) -> int:
    """File a new claim as `open` and record it in history. Returns the claim id.

    Raises ClaimError, and saves nothing, if any field is invalid.
    """
    passenger = _require_text(passenger, "passenger")
    flight = _require_text(flight, "flight")
    claim_type = _require_choice(claim_type, "type", CLAIM_TYPES)
    tier = _require_choice(tier, "tier", TIERS)
    changed_by = _require_text(changed_by, "changed by")

    # The claim and its first history entry are saved together or not at all.
    with conn:
        cursor = conn.execute(
            "INSERT INTO claims (passenger, flight, type, tier, status, note, filed_at, deadline) "
            "VALUES (?, ?, ?, ?, 'open', ?, ?, ?)",
            (
                passenger,
                flight,
                claim_type,
                tier,
                note or "",
                format_time(now),
                format_time(deadline_for(tier, now)),
            ),
        )
        claim_id = cursor.lastrowid
        _add_history(conn, claim_id, None, "open", changed_by, now)
    return claim_id


def get_claim(conn: sqlite3.Connection, claim_id: int) -> sqlite3.Row:
    """Return one claim, or raise ClaimError if it does not exist."""
    row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    if row is None:
        raise ClaimError(f"claim {claim_id} does not exist")
    return row


def list_claims(
    conn: sqlite3.Connection, status: str | None = None, tier: str | None = None
) -> list[sqlite3.Row]:
    """Return claims in id order, optionally only those with this status and/or tier."""
    conditions = []
    params = []
    if status is not None:
        conditions.append("status = ?")
        params.append(_require_choice(status, "status", STATUSES))
    if tier is not None:
        conditions.append("tier = ?")
        params.append(_require_choice(tier, "tier", TIERS))
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    return conn.execute(f"SELECT * FROM claims{where} ORDER BY id", params).fetchall()
