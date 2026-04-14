"""API contract and authorization tests for Battery Manager."""

from __future__ import annotations

import os

import pytest
import sqlalchemy

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")

import core
from app import app
from models import Base, KVStoreDb, UserDb


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "api_test.sqlite"
    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")

    # Ensure all code paths use the isolated test database engine.
    monkeypatch.setattr(core, "_ENGINE", engine, raising=False)
    monkeypatch.setattr(core, "_REDIS", None, raising=False)
    monkeypatch.setattr(core, "_QUEUE", None, raising=False)

    Base.metadata.create_all(engine)

    with sqlalchemy.orm.Session(engine) as session:
        session.add(UserDb(username="admin_user", password="hashed", role="admin"))
        session.add(UserDb(username="viewer_user", password="hashed", role="viewer"))
        session.commit()

    app.config["TESTING"] = True
    app.Testing = True
    with app.test_client() as test_client:
        yield test_client


def login_as(client, username: str) -> None:
    with client.session_transaction() as flask_session:
        flask_session["user_id"] = username


def test_tba_events_requires_team_key(client):
    response = client.get("/api/tba/events")

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert "team_key" in response.get_json()["message"]


def test_tba_events_rejects_non_integer_year(client):
    response = client.get("/api/tba/events?team_key=frc604&year=not-a-year")

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert "year" in response.get_json()["message"]


def test_tba_events_returns_sorted_events(client, monkeypatch):
    import api as api_module

    monkeypatch.setattr(
        api_module.tba_client,
        "get_team_events",
        lambda team_key, year: [
            {"key": "2026z", "start_date": "2026-04-20", "name": "Late Event"},
            {"key": "2026a", "start_date": "2026-03-01", "name": "Early Event"},
        ],
    )

    response = client.get("/api/tba/events?team_key=frc604&year=2026")

    assert response.status_code == 200
    payload = response.get_json()
    assert [event["key"] for event in payload] == ["2026a", "2026z"]


def test_sync_post_requires_authentication(client):
    response = client.post("/api/sync")

    assert response.status_code == 401
    assert response.get_json()["message"] == "Authentication required"


def test_sync_post_requires_admin_role(client):
    login_as(client, "viewer_user")

    response = client.post("/api/sync")

    assert response.status_code == 403
    assert response.get_json()["message"] == "Admin access required"


def test_sync_post_admin_queues_job_and_updates_kv(client, monkeypatch):
    import api as api_module

    class DummyJob:
        id = "sync-job-123"

    monkeypatch.setattr(api_module, "ensure_periodic_job", lambda *args, **kwargs: DummyJob())

    login_as(client, "admin_user")
    response = client.post("/api/sync")

    assert response.status_code == 202
    body = response.get_json()
    assert body["status"] == "success"
    assert body["data"]["job_status"] == "queued"

    with sqlalchemy.orm.Session(core.get_engine()) as session:
        kv = session.get(KVStoreDb, "last_sync_job_id")
        assert kv is not None
        assert kv.value == "sync-job-123"


def test_assign_battery_requires_authentication(client):
    response = client.post("/api/tba/assign_battery", json={"match_key": "qm1"})

    assert response.status_code == 401
    assert response.get_json()["message"] == "Authentication required"


def test_assign_battery_requires_admin_role(client):
    login_as(client, "viewer_user")

    response = client.post("/api/tba/assign_battery", json={"match_key": "qm1"})

    assert response.status_code == 403
    assert response.get_json()["message"] == "Admin access required"


def test_battery_put_requires_authentication(client):
    response = client.put("/api/battery/1", json={})

    assert response.status_code == 401
    assert response.get_json()["message"] == "Authentication required"


def test_battery_put_requires_admin_role(client):
    login_as(client, "viewer_user")

    response = client.put("/api/battery/1", json={})

    assert response.status_code == 403
    assert response.get_json()["message"] == "Admin access required"


def test_tba_matches_defaults_without_event_key(client):
    response = client.get("/api/tba/matches")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["matches"] == []
    assert payload["event_key"] is None
