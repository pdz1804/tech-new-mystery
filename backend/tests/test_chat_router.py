"""Comprehensive tests for chat router endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from jose import jwt
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def valid_token():
    """Create a valid JWT token."""
    data = {
        "sub": "test-user-123",
        "username": "testuser",
        "is_admin": False,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def invalid_token():
    """Create an invalid JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid"


@pytest.fixture
def auth_headers(valid_token):
    """Create auth headers."""
    return {"Authorization": f"Bearer {valid_token}"}


class TestAuthEnforcement:
    """Test 1: Auth enforcement."""

    def test_request_without_token_returns_401(self, client):
        """Request without token should return 401."""
        response = client.post("/v1/chat/sessions", json={"title": "Test"})
        assert response.status_code == 401

    def test_request_with_invalid_token_returns_401(self, client):
        """Request with invalid token should return 401."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.post("/v1/chat/sessions", json={"title": "Test"}, headers=headers)
        assert response.status_code == 401

    def test_request_with_valid_token_succeeds(self, client, auth_headers):
        """Request with valid token should succeed."""
        with patch("app.services.chat_service.ChatService.create_session") as mock_create:
            mock_create.return_value = {
                "session_id": "sess-123",
                "user_id": "test-user-123",
                "title": "Test Session",
                "description": None,
                "message_count": 0,
                "created_at": 1000.0,
                "updated_at": 1000.0,
                "last_message_at": 1000.0,
            }

            response = client.post(
                "/v1/chat/sessions",
                json={"title": "Test Session"},
                headers=auth_headers,
            )
            assert response.status_code == 201
            assert response.json()["success"] is True


class TestSessionValidation:
    """Test 2: Session validation."""

    def test_access_nonexistent_session_returns_404(self, client, auth_headers):
        """Accessing non-existent session should return 404."""
        with patch("app.services.chat_service.ChatService.get_session") as mock_get:
            mock_get.return_value = None

            response = client.get("/v1/chat/sessions/nonexistent-id", headers=auth_headers)
            assert response.status_code == 404

    def test_access_own_session_succeeds(self, client, auth_headers):
        """Accessing own session should succeed."""
        with patch("app.services.chat_service.ChatService.get_session") as mock_get:
            mock_get.return_value = {
                "session_id": "sess-123",
                "user_id": "test-user-123",
                "title": "My Session",
                "description": None,
                "message_count": 5,
                "created_at": 1000.0,
                "updated_at": 1005.0,
                "last_message_at": 1005.0,
            }

            response = client.get("/v1/chat/sessions/sess-123", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["data"]["session_id"] == "sess-123"

    def test_access_other_users_session_returns_403(self, client, auth_headers):
        """Accessing another user's session should fail properly."""
        with patch("app.services.chat_service.ChatService.get_session") as mock_get:
            mock_get.side_effect = ValueError("access denied")

            response = client.get("/v1/chat/sessions/other-user-sess", headers=auth_headers)
            assert response.status_code == 403


class TestSessionManagement:
    """Test 3: Session creation and listing."""

    def test_create_session_returns_session_object(self, client, auth_headers):
        """Creating a session should return session object."""
        session_data = {
            "session_id": "sess-456",
            "user_id": "test-user-123",
            "title": "New Chat",
            "description": "Test description",
            "message_count": 0,
            "created_at": 2000.0,
            "updated_at": 2000.0,
            "last_message_at": 2000.0,
        }

        with patch("app.services.chat_service.ChatService.create_session") as mock_create:
            mock_create.return_value = session_data

            response = client.post(
                "/v1/chat/sessions",
                json={"title": "New Chat", "description": "Test description"},
                headers=auth_headers,
            )

            assert response.status_code == 201
            assert response.json()["success"] is True
            assert response.json()["data"]["session_id"] == "sess-456"

    def test_list_sessions_returns_paginated_results(self, client, auth_headers):
        """Listing sessions should return paginated results."""
        sessions = [
            {
                "session_id": f"sess-{i}",
                "user_id": "test-user-123",
                "title": f"Session {i}",
                "description": None,
                "message_count": i,
                "created_at": 1000.0 + i,
                "updated_at": 1000.0 + i,
                "last_message_at": 1000.0 + i,
            }
            for i in range(5)
        ]

        with patch("app.services.chat_service.ChatService.list_sessions") as mock_list:
            mock_list.return_value = {
                "sessions": sessions,
                "total": 5,
                "page": 1,
                "page_size": 20,
                "has_next": False,
                "has_prev": False,
            }

            response = client.get("/v1/chat/sessions", headers=auth_headers)

            assert response.status_code == 200
            assert len(response.json()["data"]) == 5
            assert response.json()["meta"]["total"] == 5

    def test_list_sessions_sorted_by_recency(self, client, auth_headers):
        """Sessions should be sorted by last_message_at (most recent first)."""
        sessions = [
            {
                "session_id": "sess-1",
                "user_id": "test-user-123",
                "title": "Oldest",
                "description": None,
                "message_count": 0,
                "created_at": 1000.0,
                "updated_at": 1000.0,
                "last_message_at": 1000.0,
            },
            {
                "session_id": "sess-2",
                "user_id": "test-user-123",
                "title": "Newest",
                "description": None,
                "message_count": 0,
                "created_at": 1000.0,
                "updated_at": 1000.0,
                "last_message_at": 5000.0,
            },
        ]

        with patch("app.services.chat_service.ChatService.list_sessions") as mock_list:
            mock_list.return_value = {
                "sessions": sessions,
                "total": 2,
                "page": 1,
                "page_size": 20,
                "has_next": False,
                "has_prev": False,
            }

            response = client.get("/v1/chat/sessions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()["data"]
            # Most recent should come first
            assert data[0]["last_message_at"] >= data[1]["last_message_at"]


class TestMessageOperations:
    """Test 4: Message creation and retrieval."""

    def test_add_message_to_session(self, client, auth_headers):
        """Adding a message to a session should work."""
        message_data = {
            "message_id": "msg-123",
            "session_id": "sess-123",
            "user_id": "test-user-123",
            "role": "user",
            "content": "Hello, AI!",
            "timestamp": 2000.0,
            "token_count": None,
            "model_used": None,
        }

        with patch("app.services.chat_service.ChatService.add_message") as mock_add:
            mock_add.return_value = message_data

            response = client.post(
                "/v1/chat/sessions/sess-123/message",
                json={"content": "Hello, AI!"},
                headers=auth_headers,
            )

            assert response.status_code == 201
            assert response.json()["success"] is True
            assert response.json()["data"]["message_id"] == "msg-123"

    def test_get_messages_with_pagination(self, client, auth_headers):
        """Getting messages should support pagination."""
        messages = [
            {
                "message_id": f"msg-{i}",
                "session_id": "sess-123",
                "user_id": "test-user-123",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "timestamp": 2000.0 + i,
                "token_count": None,
                "model_used": None,
            }
            for i in range(50)
        ]

        with patch("app.services.chat_service.ChatService.get_messages") as mock_get:
            # Page 1
            mock_get.return_value = {
                "messages": messages[:20],
                "total": 50,
                "page": 1,
                "page_size": 20,
                "has_next": True,
                "has_prev": False,
            }

            response = client.get(
                "/v1/chat/sessions/sess-123/messages?page=1&page_size=20",
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert len(response.json()["data"]) == 20
            assert response.json()["meta"]["total"] == 50

    def test_message_pagination_page_2(self, client, auth_headers):
        """Pagination should work for page 2."""
        messages = [
            {
                "message_id": f"msg-{i}",
                "session_id": "sess-123",
                "user_id": "test-user-123",
                "role": "user",
                "content": f"Message {i}",
                "timestamp": 2000.0 + i,
                "token_count": None,
                "model_used": None,
            }
            for i in range(20, 40)
        ]

        with patch("app.services.chat_service.ChatService.get_messages") as mock_get:
            mock_get.return_value = {
                "messages": messages,
                "total": 50,
                "page": 2,
                "page_size": 20,
                "has_next": True,
                "has_prev": True,
            }

            response = client.get(
                "/v1/chat/sessions/sess-123/messages?page=2&page_size=20",
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert len(response.json()["data"]) == 20
            assert response.json()["meta"]["page"] == 2


class TestErrorHandling:
    """Test 5: Error handling."""

    def test_message_to_nonexistent_session_returns_404(self, client, auth_headers):
        """Adding message to non-existent session should return 404."""
        with patch("app.services.chat_service.ChatService.add_message") as mock_add:
            mock_add.side_effect = ValueError("Session not found")

            response = client.post(
                "/v1/chat/sessions/nonexistent/message",
                json={"content": "Test"},
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_get_messages_from_nonexistent_session_returns_404(self, client, auth_headers):
        """Getting messages from non-existent session should return 404."""
        with patch("app.services.chat_service.ChatService.get_messages") as mock_get:
            mock_get.side_effect = ValueError("Session not found")

            response = client.get(
                "/v1/chat/sessions/nonexistent/messages",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_invalid_content_validation(self, client, auth_headers):
        """Empty or invalid content should fail validation."""
        response = client.post(
            "/v1/chat/sessions/sess-123/message",
            json={"content": ""},
            headers=auth_headers,
        )

        # Should fail validation
        assert response.status_code in (422, 400)

    def test_session_title_validation(self, client, auth_headers):
        """Session title validation should work."""
        response = client.post(
            "/v1/chat/sessions",
            json={"title": ""},
            headers=auth_headers,
        )

        # Should fail validation
        assert response.status_code in (422, 400)


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_session_workflow(self, client, auth_headers):
        """Test complete workflow: create -> list -> get -> add message."""
        # Create session
        with patch("app.services.chat_service.ChatService.create_session") as mock_create:
            mock_create.return_value = {
                "session_id": "sess-workflow",
                "user_id": "test-user-123",
                "title": "Workflow Test",
                "description": None,
                "message_count": 0,
                "created_at": 1000.0,
                "updated_at": 1000.0,
                "last_message_at": 1000.0,
            }

            response = client.post(
                "/v1/chat/sessions",
                json={"title": "Workflow Test"},
                headers=auth_headers,
            )
            assert response.status_code == 201
            session_id = response.json()["data"]["session_id"]

        # List sessions
        with patch("app.services.chat_service.ChatService.list_sessions") as mock_list:
            mock_list.return_value = {
                "sessions": [
                    {
                        "session_id": session_id,
                        "user_id": "test-user-123",
                        "title": "Workflow Test",
                        "description": None,
                        "message_count": 0,
                        "created_at": 1000.0,
                        "updated_at": 1000.0,
                        "last_message_at": 1000.0,
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "has_next": False,
                "has_prev": False,
            }

            response = client.get("/v1/chat/sessions", headers=auth_headers)
            assert response.status_code == 200
            assert len(response.json()["data"]) == 1

        # Add message
        with patch("app.services.chat_service.ChatService.add_message") as mock_add:
            mock_add.return_value = {
                "message_id": "msg-workflow",
                "session_id": session_id,
                "user_id": "test-user-123",
                "role": "user",
                "content": "Test message",
                "timestamp": 2000.0,
                "token_count": None,
                "model_used": None,
            }

            response = client.post(
                f"/v1/chat/sessions/{session_id}/message",
                json={"content": "Test message"},
                headers=auth_headers,
            )
            assert response.status_code == 201
            assert response.json()["data"]["message_id"] == "msg-workflow"

        # Get messages
        with patch("app.services.chat_service.ChatService.get_messages") as mock_get:
            mock_get.return_value = {
                "messages": [
                    {
                        "message_id": "msg-workflow",
                        "session_id": session_id,
                        "user_id": "test-user-123",
                        "role": "user",
                        "content": "Test message",
                        "timestamp": 2000.0,
                        "token_count": None,
                        "model_used": None,
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "has_next": False,
                "has_prev": False,
            }

            response = client.get(
                f"/v1/chat/sessions/{session_id}/messages",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert len(response.json()["data"]) == 1
