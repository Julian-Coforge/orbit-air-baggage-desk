"""Shared fixtures: a fresh in-memory database and a fixed clock."""

from datetime import UTC, datetime

import pytest

import db

# Every test uses this time instead of the real clock.
NOW = datetime(2026, 11, 2, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def now():
    return NOW
