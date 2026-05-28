"""
Comprehensive tests for Agent Core Memory.
Tests cover: initialization, logging, context retrieval, TTL, isolation, event structure, and configuration.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from app.integrations.agent_core_memory import (
    AgentCoreMemory,
    MemoryEvent,
    get_agent_memory,
)


@pytest.fixture
def memory_service():
    """Create fresh AgentCoreMemory instance for each test."""
    return AgentCoreMemory()


# No singleton to reset - each test gets fresh memory instance via fixture


class TestMemoryInitialization:
    """Test 1: Memory initialization with recent events."""

    @pytest.mark.asyncio
    async def test_memory_initialization_basic(self, memory_service):
        """BASIC: Initialize memory for a session."""
        result = await memory_service.initialize_memory("sess-1", "user-1")

        assert result["status"] == "initialized"
        assert result["session_id"] == "sess-1"
        assert result["user_id"] == "user-1"
        assert result["memory_type"] == "SHORT_TERM"
        assert result["event_count"] == 0

    @pytest.mark.asyncio
    async def test_memory_initialization_with_recent_events(self, memory_service):
        """HARD: Initialize memory with 10 recent events from DynamoDB."""
        recent_events = [
            {
                "event_id": f"evt-{i}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "timestamp": time.time() - (10 - i),
            }
            for i in range(10)
        ]

        result = await memory_service.initialize_memory("sess-1", "user-1", recent_events)

        assert result["status"] == "initialized"
        assert result["event_count"] == 10
        # Verify events were loaded
        context = await memory_service.get_memory_context("sess-1")
        assert len(context) == 10

    @pytest.mark.asyncio
    async def test_memory_initialization_preserves_event_structure(self, memory_service):
        """COMPLEX: Verify loaded events have correct structure."""
        recent_events = [
            {
                "event_id": "evt-1",
                "role": "user",
                "content": "Hello",
                "timestamp": 1234567890.0,
            }
        ]

        await memory_service.initialize_memory("sess-1", "user-1", recent_events)
        context = await memory_service.get_memory_context("sess-1")

        assert len(context) == 1
        event = context[0]
        assert event["role"] == "user"
        assert event["content"] == "Hello"
        assert event["timestamp"] == 1234567890.0
        assert event["session_id"] == "sess-1"

    @pytest.mark.asyncio
    async def test_memory_initialization_retention_setting(self, memory_service):
        """COMPLEX: Verify retention settings are correct."""
        result = await memory_service.initialize_memory("sess-1", "user-1")

        assert result["retention_days"] == 90


class TestMemoryLogging:
    """Test 2: Message logging to memory."""

    @pytest.mark.asyncio
    async def test_log_user_message(self, memory_service):
        """BASIC: Log a user message."""
        result = await memory_service.log_message("sess-1", "user", "Hello AI")

        assert result["status"] == "logged"
        assert result["role"] == "user"
        assert result["session_id"] == "sess-1"
        assert "event_id" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_log_assistant_message(self, memory_service):
        """BASIC: Log an assistant message."""
        result = await memory_service.log_message("sess-1", "assistant", "Hello user")

        assert result["status"] == "logged"
        assert result["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_log_multiple_messages_in_order(self, memory_service):
        """HARD: Log 5 messages alternating user/assistant."""
        messages = [
            ("user", "Message 1"),
            ("assistant", "Response 1"),
            ("user", "Message 2"),
            ("assistant", "Response 2"),
            ("user", "Message 3"),
        ]

        for role, content in messages:
            await memory_service.log_message("sess-1", role, content)

        context = await memory_service.get_memory_context("sess-1")
        assert len(context) == 5

        for i, (expected_role, expected_content) in enumerate(messages):
            assert context[i]["role"] == expected_role
            assert context[i]["content"] == expected_content

    @pytest.mark.asyncio
    async def test_log_message_with_custom_timestamp(self, memory_service):
        """HARD: Log message with custom timestamp."""
        custom_timestamp = 1234567890.0
        result = await memory_service.log_message(
            "sess-1", "user", "Timestamped message", timestamp=custom_timestamp
        )

        assert result["timestamp"] == custom_timestamp

    @pytest.mark.asyncio
    async def test_log_message_defaults_to_current_time(self, memory_service):
        """HARD: Verify timestamp defaults to current time."""
        before = time.time()
        result = await memory_service.log_message("sess-1", "user", "Current time message")
        after = time.time()

        assert before <= result["timestamp"] <= after

    @pytest.mark.asyncio
    async def test_log_message_invalid_role(self, memory_service):
        """EDGE: Reject invalid role."""
        with pytest.raises(ValueError, match="Invalid role"):
            await memory_service.log_message("sess-1", "invalid_role", "Content")

    @pytest.mark.asyncio
    async def test_log_message_empty_content(self, memory_service):
        """EDGE: Reject empty content."""
        with pytest.raises(ValueError, match="Content must be a non-empty string"):
            await memory_service.log_message("sess-1", "user", "")

    @pytest.mark.asyncio
    async def test_log_message_none_content(self, memory_service):
        """EDGE: Reject None content."""
        with pytest.raises(ValueError, match="Content must be a non-empty string"):
            await memory_service.log_message("sess-1", "user", None)


class TestMemoryContextRetrieval:
    """Test 3: Memory context retrieval."""

    @pytest.mark.asyncio
    async def test_get_memory_context_returns_list(self, memory_service):
        """BASIC: Get memory context returns a list."""
        await memory_service.log_message("sess-1", "user", "Test")
        context = await memory_service.get_memory_context("sess-1")

        assert isinstance(context, list)
        assert len(context) == 1

    @pytest.mark.asyncio
    async def test_get_memory_context_empty_session(self, memory_service):
        """EDGE: Get context for non-existent session returns empty list."""
        context = await memory_service.get_memory_context("nonexistent-sess")

        assert isinstance(context, list)
        assert len(context) == 0

    @pytest.mark.asyncio
    async def test_get_memory_context_sorted_by_timestamp(self, memory_service):
        """COMPLEX: Verify events are sorted by timestamp."""
        # Add messages in non-chronological order
        t1 = time.time()
        t2 = t1 + 1
        t3 = t1 + 2

        await memory_service.log_message("sess-1", "user", "First", timestamp=t1)
        await memory_service.log_message("sess-1", "user", "Third", timestamp=t3)
        await memory_service.log_message("sess-1", "user", "Second", timestamp=t2)

        context = await memory_service.get_memory_context("sess-1")

        assert len(context) == 3
        assert context[0]["content"] == "First"
        assert context[1]["content"] == "Second"
        assert context[2]["content"] == "Third"

    @pytest.mark.asyncio
    async def test_get_memory_context_all_fields_present(self, memory_service):
        """COMPLEX: Verify all required fields in retrieved events."""
        await memory_service.log_message("sess-1", "user", "Test message")
        context = await memory_service.get_memory_context("sess-1")

        event = context[0]
        assert "event_id" in event
        assert "role" in event
        assert "content" in event
        assert "timestamp" in event
        assert "session_id" in event

    @pytest.mark.asyncio
    async def test_get_memory_context_with_limit(self, memory_service):
        """HARD: Get memory context with limit parameter."""
        for i in range(5):
            await memory_service.log_message("sess-1", "user", f"Message {i}")

        # Get last 3 events
        events = await memory_service.get_memory_events("sess-1", limit=3)

        assert len(events) == 3


class TestMemoryTTLAndCleanup:
    """Test 4: Memory TTL and cleanup."""

    @pytest.mark.asyncio
    async def test_ttl_configured_90_days(self, memory_service):
        """BASIC: Verify TTL is set to 90 days."""
        assert memory_service.retention_days == 90
        assert memory_service.ttl_seconds == 90 * 86400

    @pytest.mark.asyncio
    async def test_clear_old_memory_removes_expired(self, memory_service):
        """HARD: Clear old memory removes entries > 90 days old."""
        current_time = time.time()
        old_time = current_time - (91 * 86400)  # 91 days ago
        recent_time = current_time - (10 * 86400)  # 10 days ago

        # Add old event
        await memory_service.log_message("sess-1", "user", "Old message", timestamp=old_time)
        # Add recent event
        await memory_service.log_message("sess-1", "user", "Recent message", timestamp=recent_time)

        # Clear old memory
        result = await memory_service.clear_old_memory("sess-1")

        assert result["status"] == "cleared"
        assert result["removed_count"] == 1
        assert result["remaining_count"] == 1

    @pytest.mark.asyncio
    async def test_clear_old_memory_preserves_recent(self, memory_service):
        """HARD: Clear old memory preserves recent entries."""
        current_time = time.time()

        for i in range(5):
            timestamp = current_time - (10 * 86400)  # All 10 days old
            await memory_service.log_message("sess-1", "user", f"Message {i}", timestamp=timestamp)

        result = await memory_service.clear_old_memory("sess-1")

        assert result["removed_count"] == 0
        assert result["remaining_count"] == 5

    @pytest.mark.asyncio
    async def test_clear_old_memory_nonexistent_session(self, memory_service):
        """EDGE: Clear old memory for non-existent session."""
        result = await memory_service.clear_old_memory("nonexistent-sess")

        assert result["status"] == "cleared"
        assert result["removed_count"] == 0


class TestMultiSessionIsolation:
    """Test 5: Multi-session isolation."""

    @pytest.mark.asyncio
    async def test_sessions_isolated_different_messages(self, memory_service):
        """COMPLEX: Verify session 1 has only session 1 messages."""
        # Session 1 messages
        await memory_service.log_message("sess-1", "user", "Session 1 message 1")
        await memory_service.log_message("sess-1", "user", "Session 1 message 2")

        # Session 2 messages
        await memory_service.log_message("sess-2", "user", "Session 2 message 1")
        await memory_service.log_message("sess-2", "user", "Session 2 message 2")
        await memory_service.log_message("sess-2", "user", "Session 2 message 3")

        # Get context for each session
        context1 = await memory_service.get_memory_context("sess-1")
        context2 = await memory_service.get_memory_context("sess-2")

        assert len(context1) == 2
        assert len(context2) == 3

        # Verify no leakage
        for event in context1:
            assert event["session_id"] == "sess-1"
        for event in context2:
            assert event["session_id"] == "sess-2"

    @pytest.mark.asyncio
    async def test_sessions_no_cross_contamination(self, memory_service):
        """COMPLEX: Verify no message leakage between sessions."""
        await memory_service.log_message("sess-1", "user", "Session 1 specific")
        await memory_service.log_message("sess-2", "user", "Session 2 specific")

        context1 = await memory_service.get_memory_context("sess-1")
        context2 = await memory_service.get_memory_context("sess-2")

        # Session 1 should not contain session 2 message
        contents1 = [e["content"] for e in context1]
        assert "Session 2 specific" not in contents1

        # Session 2 should not contain session 1 message
        contents2 = [e["content"] for e in context2]
        assert "Session 1 specific" not in contents2

    @pytest.mark.asyncio
    async def test_clearing_one_session_doesnt_affect_another(self, memory_service):
        """HARD: Clearing session 1 doesn't affect session 2."""
        await memory_service.log_message("sess-1", "user", "Session 1")
        await memory_service.log_message("sess-2", "user", "Session 2")

        # Delete session 1
        await memory_service.delete_session_memory("sess-1")

        # Session 2 should still have its messages
        context2 = await memory_service.get_memory_context("sess-2")
        assert len(context2) == 1
        assert context2[0]["content"] == "Session 2"


class TestEventStructureValidation:
    """Test 6: Event structure validation."""

    @pytest.mark.asyncio
    async def test_event_structure_role_field(self, memory_service):
        """BASIC: Validate role field in event."""
        await memory_service.log_message("sess-1", "user", "Test")
        context = await memory_service.get_memory_context("sess-1")
        event = context[0]

        assert "role" in event
        assert event["role"] in ("user", "assistant")

    @pytest.mark.asyncio
    async def test_event_structure_content_field(self, memory_service):
        """BASIC: Validate content field in event."""
        await memory_service.log_message("sess-1", "user", "Test content")
        context = await memory_service.get_memory_context("sess-1")
        event = context[0]

        assert "content" in event
        assert isinstance(event["content"], str)
        assert event["content"] == "Test content"

    @pytest.mark.asyncio
    async def test_event_structure_timestamp_field(self, memory_service):
        """BASIC: Validate timestamp field in event."""
        await memory_service.log_message("sess-1", "user", "Test")
        context = await memory_service.get_memory_context("sess-1")
        event = context[0]

        assert "timestamp" in event
        assert isinstance(event["timestamp"], float)

    @pytest.mark.asyncio
    async def test_event_structure_session_id_field(self, memory_service):
        """BASIC: Validate session_id field in event."""
        await memory_service.log_message("sess-1", "user", "Test")
        context = await memory_service.get_memory_context("sess-1")
        event = context[0]

        assert "session_id" in event
        assert event["session_id"] == "sess-1"

    @pytest.mark.asyncio
    async def test_validate_event_structure_valid(self, memory_service):
        """COMPLEX: Validate valid event passes validation."""
        event = {
            "role": "user",
            "content": "Valid event",
            "timestamp": time.time(),
            "session_id": "sess-1",
        }

        is_valid = await memory_service.validate_event_structure(event)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_event_structure_invalid_role(self, memory_service):
        """COMPLEX: Reject event with invalid role."""
        event = {
            "role": "invalid",
            "content": "Content",
            "timestamp": time.time(),
            "session_id": "sess-1",
        }

        with pytest.raises(ValueError, match="Invalid role"):
            await memory_service.validate_event_structure(event)

    @pytest.mark.asyncio
    async def test_validate_event_structure_missing_field(self, memory_service):
        """COMPLEX: Reject event with missing field."""
        event = {
            "role": "user",
            "content": "Content",
            # Missing timestamp
            "session_id": "sess-1",
        }

        with pytest.raises(ValueError, match="missing required fields"):
            await memory_service.validate_event_structure(event)

    @pytest.mark.asyncio
    async def test_validate_event_structure_empty_content(self, memory_service):
        """COMPLEX: Reject event with empty content."""
        event = {
            "role": "user",
            "content": "",
            "timestamp": time.time(),
            "session_id": "sess-1",
        }

        with pytest.raises(ValueError, match="non-empty string"):
            await memory_service.validate_event_structure(event)


class TestConfigurationVerification:
    """Test 7: Configuration verification."""

    def test_memory_type_short_term(self, memory_service):
        """BASIC: Verify memory type is SHORT_TERM."""
        assert memory_service.memory_type == "SHORT_TERM"

    def test_retention_days_90(self, memory_service):
        """BASIC: Verify retention is 90 days."""
        assert memory_service.retention_days == 90

    def test_ttl_seconds_calculated(self, memory_service):
        """BASIC: Verify TTL is calculated correctly."""
        expected_ttl = 90 * 86400
        assert memory_service.ttl_seconds == expected_ttl

    @pytest.mark.asyncio
    async def test_config_loads_without_error(self, memory_service):
        """COMPLEX: Verify configuration loads successfully."""
        result = await memory_service.initialize_memory("sess-1", "user-1")
        assert result["memory_type"] == "SHORT_TERM"
        assert result["retention_days"] == 90


class TestPerRequestIsolation:
    """Test per-request isolation pattern (FastAPI Depends)."""

    def test_get_agent_memory_returns_fresh_instance(self):
        """BASIC: get_agent_memory returns a fresh instance each time."""
        mem1 = get_agent_memory()
        mem2 = get_agent_memory()

        # Should be different instances (per-request isolation)
        assert mem1 is not mem2

    def test_per_request_no_state_leakage(self):
        """HARD: Each request gets isolated state (no cross-request leakage)."""
        mem1 = get_agent_memory()
        mem2 = get_agent_memory()

        # Add data to first instance
        mem1._memory_store["sess-1"] = []

        # Second instance should not have this data
        assert "sess-1" not in mem2._memory_store


class TestSessionSummary:
    """Test session summary functionality."""

    @pytest.mark.asyncio
    async def test_get_session_summary_empty(self, memory_service):
        """BASIC: Get summary for empty session."""
        summary = await memory_service.get_session_summary("sess-1")

        assert summary["session_id"] == "sess-1"
        assert summary["total_events"] == 0
        assert summary["user_messages"] == 0
        assert summary["assistant_messages"] == 0
        assert summary["retention_days"] == 90

    @pytest.mark.asyncio
    async def test_get_session_summary_with_messages(self, memory_service):
        """HARD: Get summary with mixed user/assistant messages."""
        await memory_service.log_message("sess-1", "user", "User 1")
        await memory_service.log_message("sess-1", "assistant", "Assistant 1")
        await memory_service.log_message("sess-1", "user", "User 2")

        summary = await memory_service.get_session_summary("sess-1")

        assert summary["total_events"] == 3
        assert summary["user_messages"] == 2
        assert summary["assistant_messages"] == 1


class TestDeleteSessionMemory:
    """Test session memory deletion."""

    @pytest.mark.asyncio
    async def test_delete_session_memory_existing(self, memory_service):
        """BASIC: Delete existing session memory."""
        await memory_service.log_message("sess-1", "user", "Message")
        result = await memory_service.delete_session_memory("sess-1")

        assert result["status"] == "deleted"
        assert result["deleted_count"] == 1

        # Verify deletion
        context = await memory_service.get_memory_context("sess-1")
        assert len(context) == 0

    @pytest.mark.asyncio
    async def test_delete_session_memory_nonexistent(self, memory_service):
        """EDGE: Delete non-existent session."""
        result = await memory_service.delete_session_memory("nonexistent-sess")

        assert result["status"] == "deleted"
        assert result["deleted_count"] == 0
