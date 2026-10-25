"""Outbound calls to the Telegram Bot API."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class TelegramSendError(Exception):
    """Telegram did not accept the message (network error, timeout, or non-2xx)."""


def send_message(chat_id: int, text: str) -> None:
    """Send `text` to `chat_id`; raise TelegramSendError on any failure."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise TelegramSendError("Cannot access telegram bot token")
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    # httpx error text contains api_url, which contains the token: never use
    # str(exc) in a message, and `from None` keeps it out of the traceback.
    try:
        response = httpx.post(
            api_url, json={"chat_id": chat_id, "text": text}, timeout=5
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TelegramSendError(
            f"Telegram returned {exc.response.status_code}"
        ) from None
    except httpx.HTTPError as exc:
        raise TelegramSendError(
            f"Telegram request failed: {type(exc).__name__}"
        ) from None
