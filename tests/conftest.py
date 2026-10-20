import pytest

from tally_chat_logger.db import connect


@pytest.fixture
def conn():
    conn = connect()
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def user_id(conn):
    cur = conn.execute(
        """
        INSERT INTO users (telegram_id)
        VALUES (%s)
        RETURNING id
        """,
        (787878,),
    )

    row = cur.fetchone()
    return row["id"]
