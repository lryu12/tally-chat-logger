"""create core tables

Revision ID: 6de9a19e24a9
Revises: 
Create Date: 2026-10-20 00:17:41.119940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6de9a19e24a9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            telegram_id bigint NOT NULL UNIQUE,
            timezone    text NOT NULL DEFAULT 'UTC',
            created_at  timestamptz NOT NULL DEFAULT now()
        )
    """)



def downgrade() -> None:
    op.execute("DROP TABLE users")
