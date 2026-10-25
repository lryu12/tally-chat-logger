import hmac
import logging
import os
from collections.abc import Iterator
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from tally_chat_logger.db import connect
from tally_chat_logger.telegram import TelegramSendError, send_message

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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Deliberately no database access, so platform
    health checks polling this route don't keep the database awake."""
    return {"status": "ok"}


def _allowed_user_ids() -> set[int]:
    """Parse TELEGRAM_ALLOWED_USER_IDS ("123,456") into a set of ints."""
    raw = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "")
    return {int(part) for part in raw.split(",") if part.strip()}


@app.post("/telegram/webhook")
def telegram_webhook(
    update: dict[str, Any],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    # Fail closed: an unset secret or a missing/wrong header is the same 401.
    # Compare as bytes: compare_digest raises TypeError on non-ASCII str.
    expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if (
        not expected
        or not x_telegram_bot_api_secret_token
        or not hmac.compare_digest(
            expected.encode(), x_telegram_bot_api_secret_token.encode()
        )
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Everything below returns 200 when it ignores an update: Telegram retries
    # on non-2xx, and we don't want it resending something we'll never store.
    message = update.get("message")
    if message is None:
        return {"ok": True}

    sender_id = message.get("from", {}).get("id")
    text = message.get("text")
    if sender_id not in _allowed_user_ids() or not text:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    with conn.transaction():
        # DO UPDATE (a no-op) so RETURNING yields the id on the conflict path too.
        user = conn.execute(
            """
            INSERT INTO users (telegram_id)
            VALUES (%s)
            ON CONFLICT (telegram_id) DO UPDATE SET telegram_id = EXCLUDED.telegram_id
            RETURNING id
            """,
            (sender_id,),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO raw_messages (user_id, channel, external_id, text)
            VALUES (%s, 'telegram', %s, %s)
            ON CONFLICT (channel, external_id) DO NOTHING
            """,
            (user["id"], f"{chat_id}:{message_id}", text),
        )

    # After the commit, so we never say "Saved" for something that isn't. Runs on
    # every delivery, duplicates included, so a retry re-attempts a failed reply.
    try:
        send_message(chat_id, "Saved")
    except TelegramSendError as exc:
        logger.error("reply to %s:%s failed", chat_id, message_id, exc_info=exc)
        raise HTTPException(status_code=502, detail="Reply failed")

    return {"ok": True}
