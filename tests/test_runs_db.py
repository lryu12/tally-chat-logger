from datetime import UTC, datetime
from decimal import Decimal

import psycopg
import pytest

from tally_chat_logger.activities import insert_run


def make_run(conn, user_id, **overrides):
    """Call insert_run with valid defaults; each test overrides only what it is about."""
    args = {
        "user_id": user_id,
        "occurred_at": datetime.now(UTC),
        "source": "strava",
        "external_id": "test-external-id",
        "distance_m": 5000,
        "duration_s": 1660,
    }
    args.update(overrides)
    return insert_run(conn, **args)


def count(conn, sql, params):
    """Run a SELECT count(*) ... query and return the number."""
    return conn.execute(sql, params).fetchone()["count"]


def test_insert_run_creates_activity_and_run(conn, user_id):
    result = make_run(conn, user_id)

    assert result.created is True
    assert isinstance(result.activity_id, int)

    activity = conn.execute(
        "SELECT type, source, external_id, raw_message_id FROM activities WHERE id = %s",
        (result.activity_id,),
    ).fetchone()
    assert activity["type"] == "run"
    assert activity["source"] == "strava"
    assert activity["external_id"] == "test-external-id"
    assert activity["raw_message_id"] is None

    run = conn.execute(
        "SELECT distance_m, duration_s FROM runs WHERE activity_id = %s",
        (result.activity_id,),
    ).fetchone()
    assert run["distance_m"] == Decimal("5000.00")
    assert run["duration_s"] == 1660


def test_insert_run_duplicate_returns_existing_id(conn, user_id):
    first = make_run(conn, user_id)
    second = make_run(conn, user_id)

    assert first.created is True
    assert second.created is False
    assert second.activity_id == first.activity_id


def test_insert_run_duplicate_creates_no_second_run_row(conn, user_id):
    first = make_run(conn, user_id)
    make_run(conn, user_id)

    assert (
        count(conn, "SELECT count(*) FROM activities WHERE user_id = %s", (user_id,))
        == 1
    )
    assert (
        count(
            conn,
            "SELECT count(*) FROM runs WHERE activity_id = %s",
            (first.activity_id,),
        )
        == 1
    )


def test_insert_run_duplicate_keeps_original_values(conn, user_id):
    # Documents the current behavior: a duplicate is ignored, not updated.
    first = make_run(conn, user_id, distance_m=5000)
    make_run(conn, user_id, distance_m=9999)

    run = conn.execute(
        "SELECT distance_m FROM runs WHERE activity_id = %s", (first.activity_id,)
    ).fetchone()
    assert run["distance_m"] == Decimal("5000.00")


def test_insert_run_rejects_naive_datetime(conn, user_id):
    with pytest.raises(ValueError, match="naive"):
        make_run(conn, user_id, occurred_at=datetime(2026, 10, 20, 8, 0))

    assert (
        count(conn, "SELECT count(*) FROM activities WHERE user_id = %s", (user_id,))
        == 0
    )


def test_insert_run_rolls_back_activity_if_run_insert_fails(conn, user_id):
    # distance_m = 0 passes the activities insert but violates runs' CHECK (> 0).
    with pytest.raises(psycopg.errors.CheckViolation):
        make_run(conn, user_id, distance_m=0)

    # The activity row must have been rolled back with the failed runs insert.
    assert (
        count(conn, "SELECT count(*) FROM activities WHERE user_id = %s", (user_id,))
        == 0
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"distance_m": 0},
        {"distance_m": -1},
        {"duration_s": 0},
        {"duration_s": -60},
    ],
)
def test_insert_run_rejects_nonpositive_values(conn, user_id, overrides):
    with pytest.raises(psycopg.errors.CheckViolation):
        make_run(conn, user_id, **overrides)


def test_insert_run_same_external_id_different_source_creates_both(conn, user_id):
    a = make_run(conn, user_id, source="strava")
    b = make_run(conn, user_id, source="telegram")

    assert a.created is True
    assert b.created is True
    assert a.activity_id != b.activity_id


def test_insert_run_same_external_id_different_user_creates_both(conn, user_id):
    other_user_id = conn.execute(
        "INSERT INTO users (telegram_id) VALUES (%s) RETURNING id", (787879,)
    ).fetchone()["id"]

    a = make_run(conn, user_id)
    b = make_run(conn, other_user_id)

    assert a.created is True
    assert b.created is True
    assert a.activity_id != b.activity_id


def test_insert_run_rejects_unknown_source(conn, user_id):
    # The CHECK constraint on activities.source is the guard here, not Python.
    with pytest.raises(psycopg.errors.CheckViolation):
        make_run(conn, user_id, source="test")
