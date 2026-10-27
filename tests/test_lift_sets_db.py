from decimal import Decimal

import psycopg
import pytest


def make_activity(conn, user_id, external_id="lift-1"):
    return conn.execute(
        """
        INSERT INTO activities (user_id, type, occurred_at, source, external_id)
        VALUES (%s, 'lift', now(), 'telegram', %s)
        RETURNING id
        """,
        (user_id, external_id),
    ).fetchone()["id"]


def get_exercise_id(conn, name="bench_press"):
    # Seeded by the lift tables migration.
    return conn.execute("SELECT id FROM exercises WHERE name = %s", (name,)).fetchone()[
        "id"
    ]


def make_set(conn, activity_id, exercise_id, **overrides):
    values = {"set_index": 1, "weight_lb": 135, "reps": 8, **overrides}
    return conn.execute(
        """
        INSERT INTO lift_sets (activity_id, exercise_id, set_index, weight_lb, reps)
        VALUES (%(activity_id)s, %(exercise_id)s, %(set_index)s, %(weight_lb)s, %(reps)s)
        RETURNING id
        """,
        {"activity_id": activity_id, "exercise_id": exercise_id, **values},
    ).fetchone()["id"]


def count(conn, sql, params):
    return conn.execute(sql, params).fetchone()["n"]


def test_lift_set_stores_values(conn, user_id):
    activity_id = make_activity(conn, user_id)
    exercise_id = get_exercise_id(conn)

    set_id = make_set(conn, activity_id, exercise_id, weight_lb=137.5, reps=5)

    row = conn.execute(
        "SELECT weight_lb, reps FROM lift_sets WHERE id = %s", (set_id,)
    ).fetchone()
    assert row == {"weight_lb": Decimal("137.50"), "reps": 5}


def test_lift_set_accepts_zero_weight_for_bodyweight(conn, user_id):
    activity_id = make_activity(conn, user_id)

    make_set(conn, activity_id, get_exercise_id(conn, "pull_up"), weight_lb=0)


@pytest.mark.parametrize(
    "bad",
    [{"weight_lb": -1}, {"reps": 0}, {"reps": -1}, {"set_index": 0}],
)
def test_lift_set_rejects_bad_values(conn, user_id, bad):
    activity_id = make_activity(conn, user_id)
    exercise_id = get_exercise_id(conn)

    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        make_set(conn, activity_id, exercise_id, **bad)


def test_lift_set_rejects_duplicate_set_index_for_same_exercise(conn, user_id):
    activity_id = make_activity(conn, user_id)
    exercise_id = get_exercise_id(conn)
    make_set(conn, activity_id, exercise_id, set_index=1)

    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        make_set(conn, activity_id, exercise_id, set_index=1)


def test_lift_set_same_index_for_different_exercises_is_allowed(conn, user_id):
    activity_id = make_activity(conn, user_id)

    make_set(conn, activity_id, get_exercise_id(conn, "bench_press"), set_index=1)
    make_set(conn, activity_id, get_exercise_id(conn, "squat"), set_index=1)


def test_lift_set_same_index_in_different_activities_is_allowed(conn, user_id):
    exercise_id = get_exercise_id(conn)
    first = make_activity(conn, user_id, external_id="lift-1")
    second = make_activity(conn, user_id, external_id="lift-2")

    make_set(conn, first, exercise_id, set_index=1)
    make_set(conn, second, exercise_id, set_index=1)


def test_lift_set_rejects_unknown_exercise(conn, user_id):
    activity_id = make_activity(conn, user_id)

    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        make_set(conn, activity_id, exercise_id=999_999_999)


def test_exercise_in_use_cannot_be_deleted(conn, user_id):
    activity_id = make_activity(conn, user_id)
    exercise_id = get_exercise_id(conn)
    make_set(conn, activity_id, exercise_id)

    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        conn.execute("DELETE FROM exercises WHERE id = %s", (exercise_id,))


def test_deleting_activity_deletes_its_sets(conn, user_id):
    activity_id = make_activity(conn, user_id)
    make_set(conn, activity_id, get_exercise_id(conn))

    conn.execute("DELETE FROM activities WHERE id = %s", (activity_id,))

    remaining = count(
        conn,
        "SELECT count(*) AS n FROM lift_sets WHERE activity_id = %s",
        (activity_id,),
    )
    assert remaining == 0


def test_exercise_name_must_be_lowercase(conn):
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute("INSERT INTO exercises (name) VALUES ('Leg_Press')")


def test_exercise_name_must_be_unique(conn):
    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        conn.execute("INSERT INTO exercises (name) VALUES ('bench_press')")
