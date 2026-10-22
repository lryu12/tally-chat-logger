"""create core tables

Revision ID: 6de9a19e24a9
Revises: 
Create Date: 2026-10-20 00:17:41.119940

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6de9a19e24a9'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            telegram_id bigint NOT NULL UNIQUE,
            timezone    text NOT NULL DEFAULT 'UTC',
            created_at  timestamptz NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE raw_messages (
            id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id      bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            channel      text NOT NULL,
            external_id  text NOT NULL,
            text         text NOT NULL,
            received_at  timestamptz NOT NULL DEFAULT now(),
            parse_status text NOT NULL DEFAULT 'pending'
                CHECK (parse_status IN ('pending', 'parsed', 'confirmed', 'rejected', 'failed')),
            parse_result jsonb,
            UNIQUE (channel, external_id)
        )
    """)

    op.execute("""
        CREATE TABLE activities (
            id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id        bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type           text NOT NULL CHECK (type IN ('run', 'lift', 'leetcode')),
            occurred_at    timestamptz NOT NULL,
            source         text NOT NULL CHECK (source IN ('telegram', 'strava', 'import')),
            external_id    text NOT NULL,
            raw_message_id bigint REFERENCES raw_messages(id) ON DELETE SET NULL,
            created_at     timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, source, external_id)
        )
    """)
    
    # For timeline queries, UNIQUE(user_id, source, external_id) already creates
    # indices. This is for timeline queries
    op.execute("""
        CREATE INDEX activities_user_occurred_idx
        ON activities (user_id, occurred_at DESC)
    """)

    op.execute("""
        CREATE TABLE runs (
            activity_id bigint PRIMARY KEY REFERENCES activities(id) ON DELETE CASCADE,
            distance_m  numeric(10, 2) NOT NULL CHECK (distance_m > 0),
            duration_s  integer NOT NULL CHECK (duration_s > 0)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE runs")
    op.execute("DROP TABLE activities")
    op.execute("DROP TABLE raw_messages")
    op.execute("DROP TABLE users")
