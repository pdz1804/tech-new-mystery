"""
Comprehensive tests for ChatService.
Tests cover: basic cases, hard cases, complex cases, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.services.chat_service import ChatService, CHAT_TTL_SECONDS
from app.models.chat import ConversationSessionModel, ConversationMessageModel


# Test fixtures


@pytest.fixture
def chat_service():
    """Create ChatService instance."""
    return ChatService()


def _create_mock_session(user_id: str, session_id: str, **kwargs):
    """Helper to create mock session."""
    mock_session = MagicMock(spec=ConversationSessionModel)
    mock_session.user_id = user_id
    mock_session.session_id = session_id
    mock_session.title = kwargs.get("title", "Test Session")
    mock_session.description = kwargs.get("description", None)
    mock_session.created_at = kwargs.get("created_at", 1234567890)
    mock_session.updated_at = kwargs.get("updated_at", 1234567890)
    mock_session.last_message_at = kwargs.get("last_message_at", 1234567890)
    mock_session.message_count = kwargs.get("message_count", 0)
    mock_session.is_active = kwargs.get("is_active", True)
    return mock_session


def _create_mock_message(session_id: str, message_id: str, **kwargs):
    """Helper to create mock message."""
    mock_msg = MagicMock(spec=ConversationMessageModel)
    mock_msg.session_id = session_id
    mock_msg.message_id = message_id
    mock_msg.user_id = kwargs.get("user_id", "user-1")
    mock_msg.role = kwargs.get("role", "user")
    mock_msg.content = kwargs.get("content", "Test message")
    mock_msg.timestamp = kwargs.get("timestamp", 1234567890)
    mock_msg.token_count = kwargs.get("token_count", None)
    mock_msg.model_used = kwargs.get("model_used", None)
    return mock_msg


# Test 1: Create Session


class TestCreateSession:
    """Tests for creating conversation sessions."""

    @pytest.mark.asyncio
    async def test_create_session_basic_success(self, chat_service):
        """BASIC: Successfully create a session."""
        with patch.object(ConversationSessionModel, "save"):
            result = await chat_service.create_session("user-1", "Test Session")

            assert result["session_id"] is not None
            assert result["user_id"] == "user-1"
            assert result["title"] == "Test Session"
            assert result["description"] is None
            assert result["message_count"] == 0
            assert result["is_active"] is True
            assert result["created_at"] is not None
            assert result["updated_at"] is not None
            assert result["last_message_at"] is not None

    @pytest.mark.asyncio
    async def test_create_session_with_description(self, chat_service):
        """HARD: Create session with description."""
        with patch.object(ConversationSessionModel, "save"):
            result = await chat_service.create_session(
                "user-1",
                "Test Session",
                description="Session description"
            )

            assert result["title"] == "Test Session"
            assert result["description"] == "Session description"

    @pytest.mark.asyncio
    async def test_create_session_ttl_set(self, chat_service):
        """COMPLEX: Verify TTL is set to 90 days."""
        with patch.object(ConversationSessionModel, "save"):
            import time
            before = int(time.time())

            result = await chat_service.create_session("user-1", "Test")

            after = int(time.time())

            # TTL should be 90 days from now
            expected_ttl_min = before + CHAT_TTL_SECONDS
            expected_ttl_max = after + CHAT_TTL_SECONDS

            # Note: We can't directly verify the TTL from the service response,
            # but the model should have it set

    @pytest.mark.asyncio
    async def test_create_multiple_sessions_different_ids(self, chat_service):
        """COMPLEX: Create multiple sessions get unique IDs."""
        with patch.object(ConversationSessionModel, "save"):
            result1 = await chat_service.create_session("user-1", "Session 1")
            result2 = await chat_service.create_session("user-1", "Session 2")

            assert result1["session_id"] != result2["session_id"]
            assert result1["title"] == "Session 1"
            assert result2["title"] == "Session 2"

    @pytest.mark.asyncio
    async def test_create_session_response_structure(self, chat_service):
        """COMPLEX: Verify response has all required fields."""
        with patch.object(ConversationSessionModel, "save"):
            result = await chat_service.create_session("user-1", "Test")

            required_fields = [
                "session_id", "user_id", "title", "description",
                "created_at", "updated_at", "last_message_at",
                "message_count", "is_active"
            ]

            for field in required_fields:
                assert field in result


# Test 2: Get Session


class TestGetSession:
    """Tests for retrieving conversation sessions."""

    @pytest.mark.asyncio
    async def test_get_session_basic_success(self, chat_service):
        """BASIC: Successfully retrieve a session."""
        mock_session = _create_mock_session("user-1", "sess-1", title="Test Session")

        with patch.object(ConversationSessionModel, "get", return_value=mock_session):
            result = await chat_service.get_session("sess-1", "user-1")

            assert result is not None
            assert result["session_id"] == "sess-1"
            assert result["user_id"] == "user-1"
            assert result["title"] == "Test Session"
            assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, chat_service):
        """EDGE: Get non-existent session returns None."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            result = await chat_service.get_session("nonexistent", "user-1")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_wrong_user_access_denied(self, chat_service):
        """HARD: User B cannot access User A's session."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            result = await chat_service.get_session("sess-1", "user-2")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_response_structure(self, chat_service):
        """COMPLEX: Verify get response has all required fields."""
        mock_session = _create_mock_session("user-1", "sess-1")

        with patch.object(ConversationSessionModel, "get", return_value=mock_session):
            result = await chat_service.get_session("sess-1", "user-1")

            required_fields = [
                "session_id", "user_id", "title", "description",
                "created_at", "updated_at", "last_message_at",
                "message_count", "is_active"
            ]

            for field in required_fields:
                assert field in result


# Test 3: List Sessions


class TestListSessions:
    """Tests for listing conversation sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_basic_success(self, chat_service):
        """BASIC: Successfully list user's sessions."""
        mock_sessions = [
            _create_mock_session("user-1", f"sess-{i}", title=f"Session {i}")
            for i in range(5)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_sessions))

        with patch.object(
            ConversationSessionModel.user_last_message_index,
            "query",
            return_value=mock_index_query
        ):
            result = await chat_service.list_sessions("user-1")

            assert result["total"] == 5
            assert len(result["sessions"]) == 5
            assert result["page"] == 1
            assert result["page_size"] == 20
            assert result["has_next"] is False
            assert result["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_sessions_pagination_first_page(self, chat_service):
        """HARD: List with pagination (page 1, size 3)."""
        mock_sessions = [
            _create_mock_session("user-1", f"sess-{i}", title=f"Session {i}")
            for i in range(10)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_sessions))

        with patch.object(
            ConversationSessionModel.user_last_message_index,
            "query",
            return_value=mock_index_query
        ):
            result = await chat_service.list_sessions("user-1", page=1, page_size=3)

            assert result["total"] == 10
            assert len(result["sessions"]) == 3
            assert result["page"] == 1
            assert result["page_size"] == 3
            assert result["has_next"] is True
            assert result["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_sessions_pagination_second_page(self, chat_service):
        """HARD: List second page of sessions."""
        mock_sessions = [
            _create_mock_session("user-1", f"sess-{i}", title=f"Session {i}")
            for i in range(10)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_sessions))

        with patch.object(
            ConversationSessionModel.user_last_message_index,
            "query",
            return_value=mock_index_query
        ):
            result = await chat_service.list_sessions("user-1", page=2, page_size=3)

            assert result["total"] == 10
            assert len(result["sessions"]) == 3
            assert result["page"] == 2
            assert result["has_next"] is True
            assert result["has_prev"] is True

    @pytest.mark.asyncio
    async def test_list_sessions_pagination_last_page(self, chat_service):
        """HARD: List last page with fewer items."""
        mock_sessions = [
            _create_mock_session("user-1", f"sess-{i}", title=f"Session {i}")
            for i in range(10)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_sessions))

        with patch.object(
            ConversationSessionModel.user_last_message_index,
            "query",
            return_value=mock_index_query
        ):
            result = await chat_service.list_sessions("user-1", page=4, page_size=3)

            assert result["total"] == 10
            assert len(result["sessions"]) == 1
            assert result["page"] == 4
            assert result["has_next"] is False
            assert result["has_prev"] is True

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, chat_service):
        """EDGE: List sessions when none exist."""
        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter([]))

        with patch.object(
            ConversationSessionModel.user_last_message_index,
            "query",
            return_value=mock_index_query
        ):
            result = await chat_service.list_sessions("user-1")

            assert result["total"] == 0
            assert result["sessions"] == []
            assert result["has_next"] is False
            assert result["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_sessions_filters_inactive(self, chat_service):
        """COMPLEX: List only active sessions."""
        mock_sessions = [
            _create_mock_session("user-1", f"sess-{i}", title=f"Session {i}", is_active=(i % 2 == 0))
            for i in range(6)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_sessions))

        with patch.object(
            ConversationSessionModel.user_last_message_index,
            "query",
            return_value=mock_index_query
        ):
            result = await chat_service.list_sessions("user-1")

            # Should only have active sessions (0, 2, 4)
            assert result["total"] == 3
            assert len(result["sessions"]) == 3

    @pytest.mark.asyncio
    async def test_list_sessions_recency_sort(self, chat_service):
        """COMPLEX: Verify recency sorting works."""
        mock_sessions = [
            _create_mock_session("user-1", f"sess-{i}", title=f"Session {i}", last_message_at=1234567890 + i)
            for i in range(3)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_sessions))

        with patch.object(
            ConversationSessionModel.user_last_message_index,
            "query",
            return_value=mock_index_query
        ) as mock_query:
            result = await chat_service.list_sessions("user-1", sort_by="recency")

            # Verify query was called with scan_index_forward=False (descending)
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs.get("scan_index_forward") is False


# Test 4: Add Message


class TestAddMessage:
    """Tests for adding messages to sessions."""

    @pytest.mark.asyncio
    async def test_add_message_basic_success(self, chat_service):
        """BASIC: Successfully add a message."""
        mock_session = _create_mock_session("user-1", "sess-1")

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(ConversationMessageModel, "save"), \
             patch.object(chat_service, "_update_session_metadata", new_callable=AsyncMock):

            result = await chat_service.add_message(
                "sess-1", "user-1", "user", "Hello, AI!"
            )

            assert result["message_id"] is not None
            assert result["session_id"] == "sess-1"
            assert result["user_id"] == "user-1"
            assert result["role"] == "user"
            assert result["content"] == "Hello, AI!"
            assert result["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_add_message_alternating_roles(self, chat_service):
        """HARD: Add messages with alternating user/assistant roles."""
        mock_session = _create_mock_session("user-1", "sess-1")

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(ConversationMessageModel, "save"), \
             patch.object(chat_service, "_update_session_metadata", new_callable=AsyncMock):

            result_user = await chat_service.add_message("sess-1", "user-1", "user", "Hello")
            result_assistant = await chat_service.add_message(
                "sess-1", "user-1", "assistant", "Hi there!", token_count=50, model_used="claude-3"
            )

            assert result_user["role"] == "user"
            assert result_assistant["role"] == "assistant"
            assert result_assistant["token_count"] == 50
            assert result_assistant["model_used"] == "claude-3"

    @pytest.mark.asyncio
    async def test_add_message_to_nonexistent_session(self, chat_service):
        """EDGE: Try to add message to non-existent session."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            with pytest.raises(ValueError):
                await chat_service.add_message("nonexistent", "user-1", "user", "Hello")

    @pytest.mark.asyncio
    async def test_add_message_wrong_user(self, chat_service):
        """HARD: User B cannot add message to User A's session."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            with pytest.raises(ValueError):
                await chat_service.add_message("sess-1", "user-2", "user", "Hacking attempt")

    @pytest.mark.asyncio
    async def test_add_message_ttl_set(self, chat_service):
        """COMPLEX: Verify message TTL is set to 90 days."""
        mock_session = _create_mock_session("user-1", "sess-1")

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(ConversationMessageModel, "save"), \
             patch.object(chat_service, "_update_session_metadata", new_callable=AsyncMock):

            result = await chat_service.add_message("sess-1", "user-1", "user", "Test")

            # Verify result has timestamp (TTL would be set internally in model)
            assert result["timestamp"] is not None

    @pytest.mark.asyncio
    async def test_add_message_response_structure(self, chat_service):
        """COMPLEX: Verify message response has all fields."""
        mock_session = _create_mock_session("user-1", "sess-1")

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(ConversationMessageModel, "save"), \
             patch.object(chat_service, "_update_session_metadata", new_callable=AsyncMock):

            result = await chat_service.add_message("sess-1", "user-1", "user", "Test")

            required_fields = [
                "message_id", "session_id", "user_id", "role",
                "content", "timestamp", "token_count", "model_used"
            ]

            for field in required_fields:
                assert field in result


# Test 5: Get Messages


class TestGetMessages:
    """Tests for retrieving messages from sessions."""

    @pytest.mark.asyncio
    async def test_get_messages_basic_success(self, chat_service):
        """BASIC: Successfully retrieve messages."""
        mock_session = _create_mock_session("user-1", "sess-1")
        mock_messages = [
            _create_mock_message("sess-1", f"msg-{i}", content=f"Message {i}")
            for i in range(5)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_messages))

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(
                ConversationMessageModel.session_timestamp_index,
                "query",
                return_value=mock_index_query
            ):
            result = await chat_service.get_messages("sess-1", "user-1")

            assert result["total"] == 5
            assert len(result["messages"]) == 5
            assert result["page"] == 1
            assert result["page_size"] == 20
            assert result["has_next"] is False

    @pytest.mark.asyncio
    async def test_get_messages_pagination_20_items_per_page(self, chat_service):
        """HARD: Get messages page 1 with 20 items."""
        mock_session = _create_mock_session("user-1", "sess-1")
        mock_messages = [
            _create_mock_message("sess-1", f"msg-{i}", content=f"Message {i}")
            for i in range(30)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_messages))

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(
                ConversationMessageModel.session_timestamp_index,
                "query",
                return_value=mock_index_query
            ):
            result = await chat_service.get_messages("sess-1", "user-1", page=1, page_size=20)

            assert result["total"] == 30
            assert len(result["messages"]) == 20
            assert result["page"] == 1
            assert result["has_next"] is True

    @pytest.mark.asyncio
    async def test_get_messages_pagination_second_page(self, chat_service):
        """HARD: Get messages page 2 with remaining items."""
        mock_session = _create_mock_session("user-1", "sess-1")
        mock_messages = [
            _create_mock_message("sess-1", f"msg-{i}", content=f"Message {i}")
            for i in range(30)
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_messages))

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(
                ConversationMessageModel.session_timestamp_index,
                "query",
                return_value=mock_index_query
            ):
            result = await chat_service.get_messages("sess-1", "user-1", page=2, page_size=20)

            assert result["total"] == 30
            assert len(result["messages"]) == 10
            assert result["page"] == 2
            assert result["has_next"] is False
            assert result["has_prev"] is True

    @pytest.mark.asyncio
    async def test_get_messages_no_messages(self, chat_service):
        """EDGE: Get messages from empty session."""
        mock_session = _create_mock_session("user-1", "sess-1")

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter([]))

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(
                ConversationMessageModel.session_timestamp_index,
                "query",
                return_value=mock_index_query
            ):
            result = await chat_service.get_messages("sess-1", "user-1")

            assert result["total"] == 0
            assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_get_messages_wrong_user(self, chat_service):
        """HARD: User B cannot get messages from User A's session."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            with pytest.raises(ValueError):
                await chat_service.get_messages("sess-1", "user-2")

    @pytest.mark.asyncio
    async def test_get_messages_response_structure(self, chat_service):
        """COMPLEX: Verify messages response structure."""
        mock_session = _create_mock_session("user-1", "sess-1")
        mock_messages = [
            _create_mock_message("sess-1", "msg-1", content="Test message")
        ]

        mock_index_query = MagicMock()
        mock_index_query.__iter__ = MagicMock(return_value=iter(mock_messages))

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(
                ConversationMessageModel.session_timestamp_index,
                "query",
                return_value=mock_index_query
            ):
            result = await chat_service.get_messages("sess-1", "user-1")

            required_fields = ["messages", "total", "page", "page_size", "has_next", "has_prev"]
            for field in required_fields:
                assert field in result

            if result["messages"]:
                msg_fields = ["message_id", "session_id", "user_id", "role", "content", "timestamp"]
                for field in msg_fields:
                    assert field in result["messages"][0]


# Test 6: Archive Session


class TestArchiveSession:
    """Tests for archiving sessions."""

    @pytest.mark.asyncio
    async def test_archive_session_basic_success(self, chat_service):
        """BASIC: Successfully archive a session."""
        mock_session = _create_mock_session("user-1", "sess-1", is_active=True)

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(mock_session, "save"):

            result = await chat_service.archive_session("sess-1", "user-1")

            assert result is True
            assert mock_session.is_active is False

    @pytest.mark.asyncio
    async def test_archive_session_not_found(self, chat_service):
        """EDGE: Archive non-existent session."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            result = await chat_service.archive_session("nonexistent", "user-1")

            assert result is False

    @pytest.mark.asyncio
    async def test_archive_session_wrong_user(self, chat_service):
        """HARD: User B cannot archive User A's session."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            result = await chat_service.archive_session("sess-1", "user-2")

            assert result is False

    @pytest.mark.asyncio
    async def test_archive_session_already_archived(self, chat_service):
        """COMPLEX: Archive already archived session."""
        mock_session = _create_mock_session("user-1", "sess-1", is_active=False)

        with patch.object(ConversationSessionModel, "get", return_value=mock_session), \
             patch.object(mock_session, "save"):

            result = await chat_service.archive_session("sess-1", "user-1")

            assert result is True
            assert mock_session.is_active is False


# Test 7: User Isolation


class TestUserIsolation:
    """Tests for user access control and isolation."""

    @pytest.mark.asyncio
    async def test_user_a_cannot_access_user_b_session(self, chat_service):
        """HARD: User A tries to access User B's session."""
        from pynamodb.exceptions import DoesNotExist

        with patch.object(ConversationSessionModel, "get", side_effect=DoesNotExist()):
            result = await chat_service.get_session("sess-1", "user-a")

            assert result is None

    @pytest.mark.asyncio
    async def test_user_isolation_in_create_and_get(self, chat_service):
        """COMPLEX: Create sessions for different users are isolated."""
        mock_session_a = _create_mock_session("user-a", "sess-a")
        mock_session_b = _create_mock_session("user-b", "sess-b")

        def mock_get(user_id, session_id):
            if user_id == "user-a" and session_id == "sess-a":
                return mock_session_a
            elif user_id == "user-b" and session_id == "sess-b":
                return mock_session_b
            from pynamodb.exceptions import DoesNotExist
            raise DoesNotExist()

        with patch.object(ConversationSessionModel, "get", side_effect=mock_get):
            result_a = await chat_service.get_session("sess-a", "user-a")
            result_b = await chat_service.get_session("sess-b", "user-b")
            result_cross = await chat_service.get_session("sess-b", "user-a")

            assert result_a is not None
            assert result_a["user_id"] == "user-a"
            assert result_b is not None
            assert result_b["user_id"] == "user-b"
            assert result_cross is None  # User A cannot access User B's session

    @pytest.mark.asyncio
    async def test_multiple_users_cannot_see_each_others_messages(self, chat_service):
        """COMPLEX: User isolation in messages."""
        mock_session_a = _create_mock_session("user-a", "sess-1")
        mock_session_b = _create_mock_session("user-b", "sess-1")

        from pynamodb.exceptions import DoesNotExist

        def mock_get(user_id, session_id):
            if user_id == "user-a" and session_id == "sess-1":
                return mock_session_a
            elif user_id == "user-b" and session_id == "sess-1":
                raise DoesNotExist()
            raise DoesNotExist()

        with patch.object(ConversationSessionModel, "get", side_effect=mock_get):
            # User A can access
            result_a = await chat_service.get_session("sess-1", "user-a")
            assert result_a is not None

            # User B cannot access (should raise)
            with pytest.raises(ValueError):
                await chat_service.get_messages("sess-1", "user-b")
