import logging
from collections.abc import Iterator
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from tally_chat_logger.db import connect

logger = logging.getLogger(__name__)

app = FastAPI()


@app.exception_handler(psycopg.OperationalError)
def database_unavailable(
    request: Request, exc: psycopg.OperationalError
) -> JSONResponse:
    """Any route or dependency that can't reach Postgres becomes a 503."""
    logger.error("database unavailable on %s", request.url.path, exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


def get_conn() -> Iterator[psycopg.Connection]:
    """Request-scoped connection: opened before the route, closed after it."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/health")
def health(conn: Annotated[psycopg.Connection, Depends(get_conn)]) -> dict[str, str]:
    try:
        conn.execute("SELECT 1")
        return {"status": "ok"}
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Server is down")
