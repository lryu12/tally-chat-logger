import os

import psycopg
from psycopg.rows import dict_row


def connect() -> psycopg.Connection:
    db_url = os.environ["DATABASE_URL"]
    return psycopg.connect(db_url, row_factory=dict_row, connect_timeout=5)
