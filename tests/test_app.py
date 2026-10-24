import psycopg
import pytest
from fastapi.testclient import TestClient

from tally_chat_logger import app as app_module
from tally_chat_logger.app import app, get_conn


@pytest.fixture
def client():
    yield TestClient(app)
    # Overrides are global state on the app; clear them so tests stay independent.
    app.dependency_overrides.clear()


class FakeConn:
    """Stands in for a psycopg connection and records what was done to it."""

    def __init__(self, fail_on_execute=False):
        self.fail_on_execute = fail_on_execute
        self.closed = False

    def execute(self, *args, **kwargs):
        if self.fail_on_execute:
            raise psycopg.OperationalError("connection lost mid-query")

    def close(self):
        self.closed = True


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_ok_even_when_database_is_down(client):
    # Liveness must not depend on the database; if it did, this would be a 503.
    def unreachable():
        raise psycopg.OperationalError("connection refused")
        yield

    app.dependency_overrides[get_conn] = unreachable

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_unreachable(client):
    def unreachable():
        raise psycopg.OperationalError("connection refused")
        yield  # makes this a generator, like the real dependency

    app.dependency_overrides[get_conn] = unreachable

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_health_returns_503_when_query_fails(client):
    def broken_conn():
        yield FakeConn(fail_on_execute=True)

    app.dependency_overrides[get_conn] = broken_conn

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Server is down"}


def test_get_conn_closes_connection_after_request(client, monkeypatch):
    fake = FakeConn()
    monkeypatch.setattr(app_module, "connect", lambda: fake)

    response = client.get("/health")

    assert response.status_code == 200
    assert fake.closed is True


def test_get_conn_closes_connection_even_when_route_fails(client, monkeypatch):
    fake = FakeConn(fail_on_execute=True)
    monkeypatch.setattr(app_module, "connect", lambda: fake)

    response = client.get("/health")

    assert response.status_code == 503
    assert fake.closed is True
