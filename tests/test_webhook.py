import pytest
from fastapi.testclient import TestClient

from tally_chat_logger import app as app_module
from tally_chat_logger.app import app, get_conn
from tally_chat_logger.telegram import TelegramSendError

SECRET = "test-secret"
SENDER_ID = 424242  # differs from the user_id fixture's 787878 in conftest


@pytest.fixture(autouse=True)
def sent_replies(monkeypatch):
    """Record replies instead of calling Telegram; autouse so no test can reach it."""
    replies = []
    # Patch the name where the route looks it up: in the app module.
    monkeypatch.setattr(
        app_module,
        "send_message",
        lambda chat_id, text: replies.append((chat_id, text)),
    )
    return replies


@pytest.fixture
def webhook_client(conn, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", str(SENDER_ID))

    # Open the test's transaction now. With none open, the route's
    # conn.transaction() would be the outermost one and really commit, leaking
    # rows into the dev database past the fixture's rollback.
    conn.execute("SELECT 1")

    # Hand the route the rolled-back test connection, so we can inspect what it wrote.
    def test_conn():
        yield conn

    app.dependency_overrides[get_conn] = test_conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_update(*, key="message", **overrides):
    """A Telegram-shaped update; overrides replace fields of the inner message."""
    message = {
        "message_id": 42,
        "from": {"id": SENDER_ID},
        "chat": {"id": SENDER_ID},
        "text": "ran 5k, 27:40",
    }
    message.update(overrides)
    return {"update_id": 1, key: message}


def post(client, update, secret=SECRET):
    headers = {} if secret is None else {"X-Telegram-Bot-Api-Secret-Token": secret}
    return client.post("/telegram/webhook", json=update, headers=headers)


def count(conn, sql, params):
    return conn.execute(sql, params).fetchone()["n"]


def count_users(conn, telegram_id=SENDER_ID):
    return count(
        conn, "SELECT count(*) AS n FROM users WHERE telegram_id = %s", (telegram_id,)
    )


def count_messages(conn, external_id="424242:42"):
    return count(
        conn,
        "SELECT count(*) AS n FROM raw_messages WHERE external_id = %s",
        (external_id,),
    )


def test_webhook_rejects_missing_secret(webhook_client, conn):
    response = post(webhook_client, make_update(), secret=None)

    assert response.status_code == 401
    assert count_messages(conn) == 0


def test_webhook_rejects_wrong_secret(webhook_client, conn):
    response = post(webhook_client, make_update(), secret="not-the-secret")

    assert response.status_code == 401
    assert count_messages(conn) == 0


def test_webhook_rejects_everything_when_server_secret_unset(
    webhook_client, conn, monkeypatch
):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET")

    # Even a request that "matches" an empty secret must be refused: fail closed.
    response = post(webhook_client, make_update(), secret="")

    assert response.status_code == 401
    assert count_messages(conn) == 0


def test_webhook_stores_message_from_allowed_user(webhook_client, conn):
    response = post(webhook_client, make_update())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    row = conn.execute(
        """
        SELECT r.channel, r.text, u.telegram_id
        FROM raw_messages r JOIN users u ON u.id = r.user_id
        WHERE r.external_id = %s
        """,
        ("424242:42",),
    ).fetchone()
    assert row == {
        "channel": "telegram",
        "text": "ran 5k, 27:40",
        "telegram_id": SENDER_ID,
    }


def test_webhook_ignores_sender_not_in_allowlist(webhook_client, conn):
    update = make_update(**{"from": {"id": 999}})

    response = post(webhook_client, update)

    assert response.status_code == 200
    assert count_messages(conn) == 0
    assert count_users(conn, telegram_id=999) == 0


def test_webhook_ignores_edited_message(webhook_client, conn):
    response = post(webhook_client, make_update(key="edited_message"))

    assert response.status_code == 200
    assert count_messages(conn) == 0


def test_webhook_ignores_message_without_text(webhook_client, conn):
    update = make_update()
    del update["message"]["text"]  # e.g. a photo

    response = post(webhook_client, update)

    assert response.status_code == 200
    assert count_messages(conn) == 0


def test_webhook_duplicate_delivery_stores_one_row(webhook_client, conn):
    first = post(webhook_client, make_update())
    retry = post(webhook_client, make_update())  # Telegram resending the same update

    assert first.status_code == 200
    assert retry.status_code == 200  # a retry must succeed, or Telegram keeps retrying
    assert count_users(conn) == 1
    assert count_messages(conn) == 1


def test_webhook_reuses_existing_user_for_later_messages(webhook_client, conn):
    post(webhook_client, make_update(message_id=42))
    post(webhook_client, make_update(message_id=43))

    assert count_users(conn) == 1
    assert count_messages(conn, "424242:42") == 1
    assert count_messages(conn, "424242:43") == 1


def test_webhook_replies_saved_to_the_chat(webhook_client, sent_replies):
    post(webhook_client, make_update())

    assert sent_replies == [(SENDER_ID, "Saved")]


def test_webhook_replies_again_on_duplicate_delivery(webhook_client, sent_replies):
    post(webhook_client, make_update())
    post(webhook_client, make_update())

    assert sent_replies == [(SENDER_ID, "Saved")] * 2


def _update_without_text():
    update = make_update()
    del update["message"]["text"]
    return update


@pytest.mark.parametrize(
    "update",
    [
        pytest.param(make_update(**{"from": {"id": 999}}), id="not_allowlisted"),
        pytest.param(make_update(key="edited_message"), id="edited_message"),
        pytest.param(_update_without_text(), id="no_text"),
    ],
)
def test_webhook_sends_no_reply_for_ignored_updates(
    webhook_client, sent_replies, update
):
    post(webhook_client, update)

    assert sent_replies == []


def test_webhook_sends_no_reply_when_unauthorized(webhook_client, sent_replies):
    post(webhook_client, make_update(), secret="not-the-secret")

    assert sent_replies == []


def test_webhook_failed_reply_returns_502_and_retry_replies(
    webhook_client, conn, sent_replies, monkeypatch
):
    attempts = []

    def flaky_send(chat_id, text):
        attempts.append(chat_id)
        if len(attempts) == 1:
            raise TelegramSendError("Telegram returned 500")
        sent_replies.append((chat_id, text))

    monkeypatch.setattr(app_module, "send_message", flaky_send)

    first = post(webhook_client, make_update())
    retry = post(webhook_client, make_update())  # Telegram redelivering after the 502

    assert first.status_code == 502
    assert retry.status_code == 200
    assert sent_replies == [(SENDER_ID, "Saved")]  # only the retry's reply got out
    assert count_messages(conn) == 1  # saved once, despite the failed first reply
