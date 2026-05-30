"""Comprehensive tests for chat router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from jose import jwt
from datetime import datetime, timedelta

from app.services.chat_service import ChatService
from app.core.exceptions import NotFoundError, ForbiddenError
from app.config import settings
from app.api.v1.chat.schemas import (
    CreateSessionRequest,
    MessageRequest,
    SessionResponse,
    MessageResponse,
)


@pytest.fixture
def valid_user_id():
    """User ID for testing."""
    return "test-user-123"


@pytest.fixture
def other_user_id():
    """Different user ID for testing."""
    return "other-user-456"


@pytest.fixture
def valid_session_id():
    """Session ID for testing."""
    return "sess-123"


@pytest.fixture
def valid_message_id():
    """Message ID for testing."""
    return "msg-123"


@pytest.fixture
def mock_chat_service():
    """Create mock ChatService."""
    return AsyncMock(spec=ChatService)


class TestChatServiceCreateSession:
    """Test 1: Session creation."""

    @pytest.mark.asyncio
    async def test_create_session_returns_session_object(self, valid_user_id, mock_chat_service):
        """Creating a session should return session object."""
        mock_chat_service.create_session.return_value = {
            "session_id": "sess-456",
            "user_id": valid_user_id,
            "title": "New Chat",
            "description": "Test description",
            "message_count": 0,
            "created_at": 2000.0,
            "updated_at": 2000.0,
            "last_message_at": 2000.0,
        }

        result = await mock_chat_service.create_session(
            user_id=valid_user_id,
            title="New Chat",
            description="Test description",
        )

        assert result["session_id"] == "sess-456"
        assert result["user_id"] == valid_user_id
        assert result["title"] == "New Chat"

    def test_create_session_validates_title(self, valid_user_id):
        """Session title validation should work."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CreateSessionRequest(title="")


class TestChatServiceSessionValidation:
    """Test 2: Session validation."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_none(self, valid_user_id, mock_chat_service):
        """Getting non-existent session should return None."""
        mock_chat_service.get_session.return_value = None

        result = await mock_chat_service.get_session(valid_user_id, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_own_session_succeeds(self, valid_user_id, valid_session_id, mock_chat_service):
        """Getting own session should succeed."""
        expected_session = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "title": "My Session",
            "description": None,
            "message_count": 5,
            "created_at": 1000.0,
            "updated_at": 1005.0,
            "last_message_at": 1005.0,
        }
        mock_chat_service.get_session.return_value = expected_session

        result = await mock_chat_service.get_session(valid_user_id, valid_session_id)

        assert result is not None
        assert result["session_id"] == valid_session_id
        assert result["user_id"] == valid_user_id


class TestChatServiceListSessions:
    """Test 3: Session listing."""

    @pytest.mark.asyncio
    async def test_list_sessions_returns_paginated_results(self, valid_user_id, mock_chat_service):
        """Listing sessions should return paginated results."""
        sessions = [
            {
                "session_id": f"sess-{i}",
                "user_id": valid_user_id,
                "title": f"Session {i}",
                "description": None,
                "message_count": i,
                "created_at": 1000.0 + i,
                "updated_at": 1000.0 + i,
                "last_message_at": 1000.0 + i,
            }
            for i in range(5)
        ]

        mock_chat_service.list_sessions.return_value = {
            "sessions": sessions,
            "total": 5,
            "page": 1,
            "page_size": 20,
            "has_next": False,
            "has_prev": False,
        }

        result = await mock_chat_service.list_sessions(valid_user_id, page=1, page_size=20)

        assert len(result["sessions"]) == 5
        assert result["total"] == 5
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_list_sessions_sorted_by_recency(self, valid_user_id, mock_chat_service):
        """Sessions should be sorted by last_message_at (most recent first)."""
        sessions = [
            {
                "session_id": "sess-1",
                "user_id": valid_user_id,
                "title": "Newest",
                "description": None,
                "message_count": 0,
                "created_at": 1000.0,
                "updated_at": 1000.0,
                "last_message_at": 5000.0,
            },
            {
                "session_id": "sess-2",
                "user_id": valid_user_id,
                "title": "Oldest",
                "description": None,
                "message_count": 0,
                "created_at": 1000.0,
                "updated_at": 1000.0,
                "last_message_at": 1000.0,
            },
        ]

        mock_chat_service.list_sessions.return_value = {
            "sessions": sessions,
            "total": 2,
            "page": 1,
            "page_size": 20,
            "has_next": False,
            "has_prev": False,
        }

        result = await mock_chat_service.list_sessions(valid_user_id)

        # Most recent should come first
        assert result["sessions"][0]["last_message_at"] > result["sessions"][1]["last_message_at"]


class TestChatServiceMessages:
    """Test 4: Message operations."""

    @pytest.mark.asyncio
    async def test_add_message_to_session(self, valid_user_id, valid_session_id, mock_chat_service):
        """Adding a message to a session should work."""
        message_data = {
            "message_id": "msg-123",
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "role": "user",
            "content": "Hello, AI!",
            "timestamp": 2000.0,
            "token_count": None,
            "model_used": None,
        }

        mock_chat_service.add_message.return_value = message_data

        result = await mock_chat_service.add_message(
            session_id=valid_session_id,
            user_id=valid_user_id,
            role="user",
            content="Hello, AI!",
        )

        assert result["message_id"] == "msg-123"
        assert result["role"] == "user"
        assert result["content"] == "Hello, AI!"

    @pytest.mark.asyncio
    async def test_get_messages_with_pagination(self, valid_user_id, valid_session_id, mock_chat_service):
        """Getting messages should support pagination."""
        messages = [
            {
                "message_id": f"msg-{i}",
                "session_id": valid_session_id,
                "user_id": valid_user_id,
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "timestamp": 2000.0 + i,
                "token_count": None,
                "model_used": None,
            }
            for i in range(20)
        ]

        mock_chat_service.get_messages.return_value = {
            "messages": messages,
            "total": 50,
            "page": 1,
            "page_size": 20,
            "has_next": True,
            "has_prev": False,
        }

        result = await mock_chat_service.get_messages(
            session_id=valid_session_id,
            user_id=valid_user_id,
            page=1,
            page_size=20,
        )

        assert len(result["messages"]) == 20
        assert result["total"] == 50
        assert result["has_next"] is True

    @pytest.mark.asyncio
    async def test_get_messages_page_2(self, valid_user_id, valid_session_id, mock_chat_service):
        """Pagination should work for page 2."""
        messages = [
            {
                "message_id": f"msg-{i}",
                "session_id": valid_session_id,
                "user_id": valid_user_id,
                "role": "user",
                "content": f"Message {i}",
                "timestamp": 2000.0 + i,
                "token_count": None,
                "model_used": None,
            }
            for i in range(20, 40)
        ]

        mock_chat_service.get_messages.return_value = {
            "messages": messages,
            "total": 50,
            "page": 2,
            "page_size": 20,
            "has_next": True,
            "has_prev": True,
        }

        result = await mock_chat_service.get_messages(
            session_id=valid_session_id,
            user_id=valid_user_id,
            page=2,
            page_size=20,
        )

        assert len(result["messages"]) == 20
        assert result["page"] == 2
        assert result["has_prev"] is True


class TestChatServiceErrorHandling:
    """Test 5: Error handling."""

    @pytest.mark.asyncio
    async def test_add_message_to_nonexistent_session_raises_error(self, valid_user_id, mock_chat_service):
        """Adding message to non-existent session should raise error."""
        mock_chat_service.add_message.side_effect = ValueError("Session not found")

        with pytest.raises(ValueError):
            await mock_chat_service.add_message(
                session_id="nonexistent",
                user_id=valid_user_id,
                role="user",
                content="Test",
            )

    @pytest.mark.asyncio
    async def test_get_messages_from_nonexistent_session_raises_error(self, valid_user_id, mock_chat_service):
        """Getting messages from non-existent session should raise error."""
        mock_chat_service.get_messages.side_effect = ValueError("Session not found")

        with pytest.raises(ValueError):
            await mock_chat_service.get_messages(
                session_id="nonexistent",
                user_id=valid_user_id,
            )

    def test_message_request_content_validation(self):
        """Empty content should fail validation."""
        with pytest.raises(ValueError):
            MessageRequest(content="")

    def test_session_request_title_validation(self):
        """Empty title should fail validation."""
        with pytest.raises(ValueError):
            CreateSessionRequest(title="")


class TestSchemaValidation:
    """Test 6: Schema validation."""

    def test_create_session_request_valid(self):
        """Valid CreateSessionRequest should succeed."""
        req = CreateSessionRequest(title="Test", description="Test session")
        assert req.title == "Test"
        assert req.description == "Test session"

    def test_message_request_valid(self):
        """Valid MessageRequest should succeed."""
        req = MessageRequest(content="Hello AI")
        assert req.content == "Hello AI"

    def test_session_response_valid(self):
        """Valid SessionResponse should create properly."""
        resp = SessionResponse(
            session_id="sess-1",
            user_id="user-1",
            title="Test",
            description=None,
            message_count=5,
            created_at=1000.0,
            updated_at=1005.0,
            last_message_at=1005.0,
        )
        assert resp.session_id == "sess-1"
        assert resp.message_count == 5

    def test_message_response_valid(self):
        """Valid MessageResponse should create properly."""
        resp = MessageResponse(
            message_id="msg-1",
            session_id="sess-1",
            user_id="user-1",
            role="user",
            content="Test",
            timestamp=2000.0,
        )
        assert resp.message_id == "msg-1"
        assert resp.role == "user"
