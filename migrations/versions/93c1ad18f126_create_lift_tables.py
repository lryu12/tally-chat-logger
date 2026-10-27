"""create lift tables

Revision ID: 93c1ad18f126
Revises: 6de9a19e24a9
Create Date: 2026-10-28 00:51:44.973279

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '93c1ad18f126'
down_revision: str | Sequence[str] | None = '6de9a19e24a9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE exercises (
            id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name       text NOT NULL UNIQUE CHECK (name = lower(name)),
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)

    # Seeded here so CI and a fresh clone get the same starting list.
    op.execute("""
        INSERT INTO exercises (name) VALUES
            ('bench_press'),
            ('squat'),
            ('deadlift'),
            ('overhead_press'),
            ('barbell_row'),
            ('pull_up'),
            ('dip'),
            ('romanian_deadlift')
    """)

    # exercise_id has no ON DELETE: the default RESTRICT stops an exercise that
    # still has sets from being deleted.
    op.execute("""
        CREATE TABLE lift_sets (
            id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            activity_id bigint NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
            exercise_id bigint NOT NULL REFERENCES exercises(id),
            set_index   integer NOT NULL CHECK (set_index >= 1),
            weight_lb   numeric(6, 2) NOT NULL CHECK (weight_lb >= 0),
            reps        integer NOT NULL CHECK (reps > 0),
            UNIQUE (activity_id, exercise_id, set_index)
        )
    """)

    # set_index counts sets per exercise within an activity (bench 1, 2, 3, then
    # squat 1, 2, 3). UNIQUE (activity_id, exercise_id, set_index) already indexes
    # lookups by activity_id, and by activity + exercise.
    # Postgres does not index foreign keys on its own; this serves "history of
    # one exercise over time".
    op.execute("""
        CREATE INDEX lift_sets_exercise_idx
        ON lift_sets (exercise_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE lift_sets")
    op.execute("DROP TABLE exercises")
