from dataclasses import dataclass
from datetime import datetime

import psycopg


@dataclass(frozen=True)
class InsertResult:
    activity_id: int
    created: bool


def insert_run(
    conn: psycopg.Connection,
    *,
    user_id: int,
    occurred_at: datetime,
    source: str,
    external_id: str,
    distance_m: float,
    duration_s: int,
) -> InsertResult:
    # TODO [learning target]: reject naive datetimes before touching the DB.
    # Hint: a datetime is "aware" only if utcoffset() is not None.

    # TODO [learning target]: open `with conn.transaction():` so both inserts
    # commit or roll back together.

    # TODO [learning target]: INSERT into activities (type is 'run') with
    # ON CONFLICT (user_id, source, external_id) DO NOTHING RETURNING id.
    # Use %s placeholders, never f-strings. fetchone() is None on conflict.

    # TODO [learning target]: if a row came back, INSERT into runs and return
    # created=True. If not, SELECT the existing id by the unique key and
    # return created=False without touching runs.
    raise NotImplementedError
