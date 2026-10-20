import psycopg
import os
from psycopg.rows import dict_row

def connect() -> psycopg.Connection:
    """Open a new connection. The caller owns it and must close it."""
    db_url = os.environ["DATABASE_URL"]
    if db_url is None:
        raise KeyError("DB url cannot be null")
    return psycopg.connect(db_url, row_factory=dict_row)
