from tally_chat_logger.activities import insert_run, InsertResult
from datetime import datetime, timezone
import psycopg

def test_insert_run_duplicate_returns_existing_id(user_id, conn):
    insert_result = insert_run(conn, user_id=user_id, occurred_at=datetime.now(timezone.utc), source="strava", external_id="test-external-id", distance_m=3.3, duration_s=2500)
    assert isinstance(insert_result.activity_id, int)
    assert insert_result.created is True
    cur = conn.execute(
        """
        SELECT type FROM activities
        WHERE id = %s
        """,
        (insert_result.activity_id,)
        
    )
    row = cur.fetchone()
    assert row["type"] == "run"

    insert2_result = insert_run(conn, user_id=user_id, occurred_at=datetime.now(timezone.utc), source="strava", external_id="test-external-id", distance_m=3.3, duration_s=2500)
    assert insert_result.activity_id == insert2_result.activity_id
    assert insert2_result.created is False
