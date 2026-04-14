"""
Authentication and route protection tests for Battery Manager.

Tests verify that @login_required decorator properly protects sensitive routes
and that session-based authentication works correctly.
"""

import pytest
import os
import tempfile
import sqlalchemy
from werkzeug.security import generate_password_hash

# Import Flask app and models
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")

import core
from app import app
from models import Base, UserDb


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

    Base.metadata.create_all(engine)
    
    # Create a test user
    with sqlalchemy.orm.Session(engine) as session:
        test_user = UserDb(
            username='testuser',
            password=generate_password_hash('testpass123'),
            role='admin',
        )
        session.add(test_user)
        session.commit()
    
    with app.test_client() as client:
        yield client
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


class TestAuthProtection:
    """Test that sensitive routes require authentication."""
    
    def test_settings_route_redirects_without_auth(self, client):
        """Test /settings redirects to login when not authenticated."""
        response = client.get('/settings', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_history_route_redirects_without_auth(self, client):
        """Test /history redirects to login when not authenticated."""
        response = client.get('/history', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_history_clear_route_redirects_without_auth(self, client):
        """Test /history/clear redirects to login when not authenticated."""
        response = client.post('/history/clear', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_load_matches_route_redirects_without_auth(self, client):
        """Test /load_matches redirects to login when not authenticated."""
        response = client.get('/load_matches', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location


class TestAuthenticatedAccess:
    """Test that authenticated users can access protected routes."""

    @staticmethod
    def _login(client):
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=False)
        assert response.status_code == 302
        with client.session_transaction() as flask_session:
            assert flask_session.get('user_id') == 'testuser'
    
    def test_settings_route_accessible_with_auth(self, client):
        """Test /settings is accessible when authenticated."""
        self._login(client)
        
        # Now try to access settings
        response = client.get('/settings')
        assert response.status_code == 200
        assert b'Settings' in response.data or b'settings' in response.data.lower()
    
    def test_history_route_accessible_with_auth(self, client):
        """Test /history is accessible when authenticated."""
        self._login(client)
        
        # Now try to access history
        response = client.get('/history')
        assert response.status_code == 200
        assert b'history' in response.data.lower()
    
    def test_load_matches_route_accessible_with_auth(self, client):
        """Test /load_matches is accessible when authenticated."""
        self._login(client)
        
        
        # Now try to access load_matches
        response = client.get('/load_matches')
        print(response.text)
        assert response.status_code == 200
        assert b'match' in response.data.lower() or b'Load' in response.data


class TestLoginLogout:
    """Test login/logout functionality."""
    
    def test_login_with_correct_credentials(self, client):
        """Test successful login with correct username and password."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        with client.session_transaction() as flask_session:
            assert flask_session.get('user_id') == 'testuser'
        # Should be redirected to index
        assert b'battery' in response.data.lower() or b'Battery' in response.data
    
    def test_login_with_incorrect_password(self, client):
        """Test login fails with incorrect password."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert b'Invalid username and/or password' in response.data
    
    def test_login_with_nonexistent_user(self, client):
        """Test login fails with nonexistent username."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'anypassword'
        })
        
        assert response.status_code == 200
        assert b'Invalid username and/or password' in response.data
    
    def test_logout(self, client):
        """Test logout clears session."""
        TestAuthenticatedAccess._login(client)
        
        # Then logout
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Try accessing protected route - should redirect
        response = client.get('/settings', follow_redirects=False)
        assert response.status_code == 302


class TestFlashMessages:
    """Test that appropriate flash messages are shown."""
    
    def test_login_required_flash_message(self, client):
        """Test that attempting to access protected route without auth shows flash message."""
        response = client.get('/settings', follow_redirects=True)
        assert response.status_code == 200
        # Flash message should indicate login is required
        assert b'logged in' in response.data.lower() or b'login' in response.data.lower()
    
    def test_password_missing_flash(self, client):
        """Test flash message when password not provided on login."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': ''
        })
        assert response.status_code == 200
        assert b'Password' in response.data
    
    def test_username_missing_flash(self, client):
        """Test flash message when username not provided on login."""
        response = client.post('/login', data={
            'username': '',
            'password': 'testpass123'
        })
        assert response.status_code == 200
        assert b'Username' in response.data
