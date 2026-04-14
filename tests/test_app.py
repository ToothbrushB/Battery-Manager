"""API contract and authorization tests for Battery Manager."""

from __future__ import annotations

import os

import pytest
import sqlalchemy
import tempfile
from werkzeug.security import generate_password_hash

from preferences import get_preference


os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")

import core
from app import app
from models import Base, KVStoreDb, UserDb


@pytest.fixture
def client(monkeypatch):
    """Create a test client with a temporary database."""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")

    # Ensure all app code paths use the isolated test engine.
    monkeypatch.setattr(core, "_ENGINE", engine, raising=False)
    monkeypatch.setattr(core, "_REDIS", None, raising=False)
    monkeypatch.setattr(core, "_QUEUE", None, raising=False)

    app.config['TESTING'] = True
    app.Testing = True

    Base.metadata.create_all(engine)
    
    # Create a test user
    with sqlalchemy.orm.Session(engine) as session:
        session.add(UserDb(username="admin_user", password="hashed", role="admin"))
        session.add(UserDb(username="viewer_user", password="hashed", role="viewer"))
        session.commit()
    
    with app.test_client() as client:
        yield client
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)
def login_as(client, username: str) -> None:
    with client.session_transaction() as flask_session:
        flask_session["user_id"] = username
class TestSettings:
    """Test that settings can be updated by admin users."""

    def test_update_settings_as_admin(self, client):
        login_as(client, "admin_user")
        response = client.post(
            "/settings",
            data={"tba-event-key": "test-event"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Settings updated successfully' in response.data
        assert get_preference("tba-event-key") == "test-event"