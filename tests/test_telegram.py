import traceback

import httpx
import pytest

from tally_chat_logger import telegram
from tally_chat_logger.telegram import TelegramSendError, send_message

TOKEN = "123:SECRET-TOKEN"


@pytest.fixture(autouse=True)
def bot_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)


@pytest.fixture
def fake_telegram(monkeypatch):
    """Replace httpx.post; returns an installer that gives back the recorded calls."""

    def install(*, status=200, error=None):
        calls = []

        def fake_post(url, **kwargs):
            calls.append({"url": url, **kwargs})
            if error is not None:
                # Real httpx errors mention the URL, which contains the token.
                raise error(f"failed calling {url}")
            # A real Response, so raise_for_status() behaves as in production.
            return httpx.Response(status, request=httpx.Request("POST", url))

        monkeypatch.setattr(telegram.httpx, "post", fake_post)
        return calls

    return install


def test_send_message_posts_to_telegram(fake_telegram):
    calls = fake_telegram()

    send_message(424242, "Saved")

    assert calls == [
        {
            "url": f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            "json": {"chat_id": 424242, "text": "Saved"},
            "timeout": 5,
        }
    ]


def test_send_message_without_token_raises_and_sends_nothing(
    fake_telegram, monkeypatch
):
    calls = fake_telegram()
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")

    with pytest.raises(TelegramSendError, match="bot token"):
        send_message(424242, "Saved")

    assert calls == []


@pytest.mark.parametrize("status", [400, 401, 500])
def test_send_message_raises_on_error_status(fake_telegram, status):
    fake_telegram(status=status)

    with pytest.raises(TelegramSendError, match=str(status)):
        send_message(424242, "Saved")


@pytest.mark.parametrize(
    "error", [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError]
)
def test_send_message_raises_on_network_error(fake_telegram, error):
    fake_telegram(error=error)

    with pytest.raises(TelegramSendError, match=error.__name__):
        send_message(424242, "Saved")


@pytest.mark.parametrize("failure", [{"status": 401}, {"error": httpx.ConnectTimeout}])
def test_send_message_errors_never_leak_the_token(fake_telegram, failure):
    fake_telegram(**failure)

    with pytest.raises(TelegramSendError) as excinfo:
        send_message(424242, "Saved")

    # The full traceback, chained exceptions included, is what ends up in the logs.
    printed = "".join(traceback.format_exception(excinfo.value))
    assert TOKEN not in printed
