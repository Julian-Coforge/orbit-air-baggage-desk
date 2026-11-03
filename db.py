"""Opens the SQLite database and creates the claims and history tables."""

import sqlite3

DEFAULT_DB_PATH = "orbit_air.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    passenger TEXT    NOT NULL CHECK (length(trim(passenger)) > 0),
    flight    TEXT    NOT NULL CHECK (length(trim(flight)) > 0),
    type      TEXT    NOT NULL CHECK (type IN ('delayed', 'lost', 'damaged')),
    tier      TEXT    NOT NULL CHECK (tier IN ('standard', 'silver', 'gold')),
    status    TEXT    NOT NULL DEFAULT 'open'
                      CHECK (status IN ('open', 'assigned', 'escalated', 'resolved', 'closed')),
    agent     TEXT,
    note      TEXT    NOT NULL DEFAULT '',
    filed_at  TEXT    NOT NULL,
    deadline  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id   INTEGER NOT NULL REFERENCES claims (id),
    old_status TEXT
               CHECK (old_status IS NULL
                      OR old_status IN ('open', 'assigned', 'escalated', 'resolved', 'closed')),
    new_status TEXT    NOT NULL
               CHECK (new_status IN ('open', 'assigned', 'escalated', 'resolved', 'closed')),
    changed_by TEXT    NOT NULL,
    changed_at TEXT    NOT NULL
);
"""


def connect(path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open the database at `path`, creating the tables if they do not exist yet."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the claims and history tables. Safe to run more than once."""
    conn.executescript(SCHEMA)
