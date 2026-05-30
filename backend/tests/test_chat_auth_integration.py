"""Integration tests for chat auth with real FastAPI endpoints."""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.core.security import create_access_token
from app.services.chat_service import ChatService


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def valid_user_id():
    """Valid user ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def other_user_id():
    """Different user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def valid_token(valid_user_id):
    """Valid JWT token."""
    return create_access_token({
        "sub": valid_user_id,
        "username": "testuser",
        "is_admin": False
    })


@pytest.fixture
def other_token(other_user_id):
    """JWT token for different user."""
    return create_access_token({
        "sub": other_user_id,
        "username": "otheruser",
        "is_admin": False
    })


@pytest.fixture
def valid_session_id():
    """Valid session ID."""
    return f"sess-{uuid.uuid4().hex[:12]}"


# ============================================================================
# CREATE SESSION TESTS
# ============================================================================

class TestCreateSessionAuth:
    """Test authentication on POST /api/v1/chat/sessions."""

    def test_create_session_without_token(self, client):
        """Should return 401 when token is missing."""
        response = client.post(
            "/api/v1/chat/sessions",
            json={"title": "New Session"},
        )
        assert response.status_code == 401

    def test_create_session_with_invalid_token(self, client):
        """Should return 401 with invalid token."""
        response = client.post(
            "/api/v1/chat/sessions",
            headers={"Authorization": "Bearer invalid.token"},
            json={"title": "New Session"},
        )
        assert response.status_code == 401

    def test_create_session_with_wrong_bearer_format(self, client, valid_token):
        """Should return 401 with wrong Bearer format."""
        response = client.post(
            "/api/v1/chat/sessions",
            headers={"Authorization": f"NotBearer {valid_token}"},
            json={"title": "New Session"},
        )
        assert response.status_code == 401

    @patch("app.services.chat_service.ChatService.create_session")
    def test_create_session_with_valid_token(self, mock_create, client, valid_token, valid_user_id):
        """Should succeed with valid token."""
        # Mock the service
        mock_create.return_value = {
            "session_id": "sess-123",
            "user_id": valid_user_id,
            "title": "New Session",
            "description": None,
            "created_at": 1000.0,
            "updated_at": 1000.0,
            "last_message_at": 1000.0,
            "message_count": 0,
            "is_active": True,
        }

        response = client.post(
            "/api/v1/chat/sessions",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"title": "New Session"},
        )
        assert response.status_code == 201
        assert response.json()["success"] is True


# ============================================================================
# LIST SESSIONS TESTS
# ============================================================================

class TestListSessionsAuth:
    """Test authentication on GET /api/v1/chat/sessions."""

    def test_list_sessions_without_token(self, client):
        """Should return 401 when token is missing."""
        response = client.get("/api/v1/chat/sessions")
        assert response.status_code == 401

    def test_list_sessions_with_invalid_token(self, client):
        """Should return 401 with invalid token."""
        response = client.get(
            "/api/v1/chat/sessions",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert response.status_code == 401

    @patch("app.services.chat_service.ChatService.list_sessions")
    def test_list_sessions_with_valid_token(self, mock_list, client, valid_token):
        """Should succeed with valid token."""
        mock_list.return_value = {
            "sessions": [],
            "page": 1,
            "page_size": 20,
            "total": 0,
        }

        response = client.get(
            "/api/v1/chat/sessions",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


# ============================================================================
# GET SESSION TESTS
# ============================================================================

class TestGetSessionAuth:
    """Test authentication on GET /api/v1/chat/sessions/{session_id}."""

    def test_get_session_without_token(self, client, valid_session_id):
        """Should return 401 when token is missing."""
        response = client.get(f"/api/v1/chat/sessions/{valid_session_id}")
        assert response.status_code == 401

    def test_get_session_with_invalid_token(self, client, valid_session_id):
        """Should return 401 with invalid token."""
        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert response.status_code == 401

    @patch("app.services.chat_service.ChatService.get_session")
    def test_get_nonexistent_session(self, mock_get, client, valid_token, valid_session_id):
        """Should return 404 for non-existent session."""
        mock_get.return_value = None

        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 404

    @patch("app.services.chat_service.ChatService.get_session")
    def test_get_session_wrong_owner(
        self,
        mock_get,
        client,
        valid_token,
        valid_user_id,
        other_user_id,
        valid_session_id,
    ):
        """Should return 403 when user doesn't own session."""
        # Session belongs to other user
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": other_user_id,
            "title": "Other's Session",
            "is_active": True,
        }

        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 403

    @patch("app.services.chat_service.ChatService.get_session")
    def test_get_session_inactive(self, mock_get, client, valid_token, valid_user_id, valid_session_id):
        """Should return 403 for inactive session."""
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "title": "Archived Session",
            "is_active": False,
        }

        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 403

    @patch("app.services.chat_service.ChatService.get_session")
    def test_get_session_success(self, mock_get, client, valid_token, valid_user_id, valid_session_id):
        """Should succeed with valid token and ownership."""
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "title": "My Session",
            "created_at": 1000.0,
            "updated_at": 1000.0,
            "last_message_at": 1000.0,
            "message_count": 5,
            "is_active": True,
        }

        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["session_id"] == valid_session_id


# ============================================================================
# GET MESSAGES TESTS
# ============================================================================

class TestGetMessagesAuth:
    """Test authentication on GET /api/v1/chat/sessions/{session_id}/messages."""

    def test_get_messages_without_token(self, client, valid_session_id):
        """Should return 401 when token is missing."""
        response = client.get(f"/api/v1/chat/sessions/{valid_session_id}/messages")
        assert response.status_code == 401

    def test_get_messages_with_invalid_token(self, client, valid_session_id):
        """Should return 401 with invalid token."""
        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}/messages",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert response.status_code == 401

    @patch("app.services.chat_service.ChatService.get_session")
    def test_get_messages_nonexistent_session(
        self,
        mock_get,
        client,
        valid_token,
        valid_session_id,
    ):
        """Should return 404 for non-existent session."""
        mock_get.return_value = None

        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}/messages",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 404

    @patch("app.services.chat_service.ChatService.get_session")
    def test_get_messages_wrong_owner(
        self,
        mock_get,
        client,
        valid_token,
        valid_user_id,
        other_user_id,
        valid_session_id,
    ):
        """Should return 403 when user doesn't own session."""
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": other_user_id,
            "is_active": True,
        }

        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}/messages",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 403

    @patch("app.services.chat_service.ChatService.get_session")
    @patch("app.services.chat_service.ChatService.get_messages")
    def test_get_messages_success(
        self,
        mock_msgs,
        mock_get,
        client,
        valid_token,
        valid_user_id,
        valid_session_id,
    ):
        """Should succeed with valid token and ownership."""
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "is_active": True,
        }
        mock_msgs.return_value = {
            "messages": [],
            "page": 1,
            "page_size": 20,
            "total": 0,
        }

        response = client.get(
            f"/api/v1/chat/sessions/{valid_session_id}/messages",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


# ============================================================================
# ADD MESSAGE TESTS
# ============================================================================

class TestAddMessageAuth:
    """Test authentication on POST /api/v1/chat/sessions/{session_id}/message."""

    def test_add_message_without_token(self, client, valid_session_id):
        """Should return 401 when token is missing."""
        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/message",
            json={"content": "Hello"},
        )
        assert response.status_code == 401

    def test_add_message_with_invalid_token(self, client, valid_session_id):
        """Should return 401 with invalid token."""
        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/message",
            headers={"Authorization": "Bearer invalid.token"},
            json={"content": "Hello"},
        )
        assert response.status_code == 401

    @patch("app.services.chat_service.ChatService.get_session")
    def test_add_message_nonexistent_session(
        self,
        mock_get,
        client,
        valid_token,
        valid_session_id,
    ):
        """Should return 404 for non-existent session."""
        mock_get.return_value = None

        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/message",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"content": "Hello"},
        )
        assert response.status_code == 404

    @patch("app.services.chat_service.ChatService.get_session")
    def test_add_message_wrong_owner(
        self,
        mock_get,
        client,
        valid_token,
        valid_user_id,
        other_user_id,
        valid_session_id,
    ):
        """Should return 403 when user doesn't own session."""
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": other_user_id,
            "is_active": True,
        }

        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/message",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"content": "Hello"},
        )
        assert response.status_code == 403

    @patch("app.services.chat_service.ChatService.get_session")
    @patch("app.services.chat_service.ChatService.add_message")
    def test_add_message_success(
        self,
        mock_add,
        mock_get,
        client,
        valid_token,
        valid_user_id,
        valid_session_id,
    ):
        """Should succeed with valid token and ownership."""
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "is_active": True,
        }
        mock_add.return_value = {
            "message_id": "msg-123",
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "role": "user",
            "content": "Hello",
            "timestamp": 1000.0,
        }

        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/message",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"content": "Hello"},
        )
        assert response.status_code == 201
        assert response.json()["success"] is True


# ============================================================================
# STREAM MESSAGE TESTS
# ============================================================================

class TestStreamMessageAuth:
    """Test authentication on POST /api/v1/chat/sessions/{session_id}/stream."""

    def test_stream_message_without_token(self, client, valid_session_id):
        """Should return 401 when token is missing."""
        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/stream",
            json={"content": "Hello"},
        )
        assert response.status_code == 401

    def test_stream_message_with_invalid_token(self, client, valid_session_id):
        """Should return 401 with invalid token."""
        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/stream",
            headers={"Authorization": "Bearer invalid.token"},
            json={"content": "Hello"},
        )
        assert response.status_code == 401

    @patch("app.services.chat_service.ChatService.get_session")
    def test_stream_message_nonexistent_session(
        self,
        mock_get,
        client,
        valid_token,
        valid_session_id,
    ):
        """Should return 404 for non-existent session."""
        mock_get.return_value = None

        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/stream",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"content": "Hello"},
        )
        assert response.status_code == 404

    @patch("app.services.chat_service.ChatService.get_session")
    def test_stream_message_wrong_owner(
        self,
        mock_get,
        client,
        valid_token,
        valid_user_id,
        other_user_id,
        valid_session_id,
    ):
        """Should return 403 when user doesn't own session."""
        mock_get.return_value = {
            "session_id": valid_session_id,
            "user_id": other_user_id,
            "is_active": True,
        }

        response = client.post(
            f"/api/v1/chat/sessions/{valid_session_id}/stream",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"content": "Hello"},
        )
        assert response.status_code == 403


# ============================================================================
# HTTP HEADER TESTS
# ============================================================================

class TestHTTPHeaders:
    """Test correct HTTP headers in auth responses."""

    def test_401_response_includes_www_authenticate(self, client):
        """401 response should include WWW-Authenticate header."""
        response = client.post(
            "/api/v1/chat/sessions",
            json={"title": "Test"},
        )
        assert response.status_code == 401
        assert "www-authenticate" in response.headers or "WWW-Authenticate" in response.headers

    def test_404_response_no_auth_header(self, client, valid_token, valid_session_id):
        """404 response should not include WWW-Authenticate header."""
        with patch("app.services.chat_service.ChatService.get_session") as mock_get:
            mock_get.return_value = None
            response = client.get(
                f"/api/v1/chat/sessions/{valid_session_id}",
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            assert response.status_code == 404
            # 404 should not have auth header
            assert "www-authenticate" not in response.headers.get("", "").lower()
