from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import psycopg


@dataclass(frozen=True)
class InsertResult:
    activity_id: int
    created: bool


class ActivityType(StrEnum):
    RUN = "run"
    LIFT = "lift"
    LEETCODE = "leetcode"


def insert_run(
    conn: psycopg.Connection,
    *,
    user_id: int,
    occurred_at: datetime,
    source: str,
    external_id: str,
    raw_message_id: int | None = None,
    distance_m: float,
    duration_s: int,
) -> InsertResult:

    if occurred_at.tzinfo is None or occurred_at.tzinfo.utcoffset(occurred_at) is None:
        raise ValueError("Can't accept naive datetimes")

    insert_result = None

    with conn.transaction():
        cur = conn.execute(
            """
            INSERT INTO activities (user_id, type, occurred_at, source, 
            external_id, raw_message_id) VALUES
            (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, source, external_id) DO NOTHING
            RETURNING id
            """,
            (
                user_id,
                ActivityType.RUN.value,
                occurred_at,
                source,
                external_id,
                raw_message_id,
            ),
        )

        activity_id_dict = cur.fetchone()
        if activity_id_dict:
            conn.execute(
                """
                INSERT INTO runs (activity_id, distance_m, duration_s) VALUES
                (%s, %s, %s)
                """,
                (activity_id_dict["id"], distance_m, duration_s),
            )
            insert_result = InsertResult(
                activity_id=activity_id_dict["id"], created=True
            )
        else:
            cur = conn.execute(
                """
                SELECT id FROM activities
                WHERE  user_id = %s AND source = %s AND external_id = %s
                """,
                (user_id, source, external_id),
            )
            existing_id_dict = cur.fetchone()
            insert_result = InsertResult(
                activity_id=existing_id_dict["id"], created=False
            )

    return insert_result
