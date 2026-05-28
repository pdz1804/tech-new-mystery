"""
Integration tests for Agent Core Memory with DynamoDB-like operations.
Tests verify end-to-end scenarios with persistence and multi-session workflows.
"""

import pytest
import time
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from app.integrations.agent_core_memory import (
    AgentCoreMemory,
    MemoryEvent,
    get_agent_memory,
)
from app.config import settings


@pytest.fixture
def memory_service():
    """Create fresh AgentCoreMemory instance for each test."""
    return AgentCoreMemory()


# No singleton to reset - each test gets fresh memory instance via fixture


class TestMemoryPersistenceScenarios:
    """Test realistic conversation persistence scenarios."""

    @pytest.mark.asyncio
    async def test_conversation_persistence_workflow(self, memory_service):
        """COMPLEX: Simulate a full conversation persistence workflow."""
        session_id = "user-conv-001"
        user_id = "user-123"

        # Step 1: Initialize memory for a new session
        init_result = await memory_service.initialize_memory(session_id, user_id)
        assert init_result["status"] == "initialized"
        assert init_result["event_count"] == 0

        # Step 2: User starts a conversation
        msg1 = await memory_service.log_message(session_id, "user", "What's new in AI?")
        assert msg1["status"] == "logged"

        # Step 3: Assistant responds
        msg2 = await memory_service.log_message(
            session_id, "assistant", "Recent AI advances include...", timestamp=msg1["timestamp"] + 1
        )
        assert msg2["status"] == "logged"

        # Step 4: User continues conversation
        msg3 = await memory_service.log_message(session_id, "user", "Tell me more about transformers")
        assert msg3["status"] == "logged"

        # Step 5: Retrieve conversation history
        history = await memory_service.get_memory_context(session_id)
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"

        # Step 6: Verify conversation is properly ordered
        for i in range(1, len(history)):
            assert history[i]["timestamp"] >= history[i - 1]["timestamp"]

    @pytest.mark.asyncio
    async def test_session_recovery_from_previous_events(self, memory_service):
        """HARD: Recover a session by loading previous events from DynamoDB."""
        session_id = "recovered-session"
        user_id = "user-456"

        # Simulate loading previous session events from DynamoDB
        previous_events = [
            {
                "event_id": "evt-1",
                "role": "user",
                "content": "First message",
                "timestamp": time.time() - 3600,  # 1 hour ago
            },
            {
                "event_id": "evt-2",
                "role": "assistant",
                "content": "First response",
                "timestamp": time.time() - 3500,
            },
            {
                "event_id": "evt-3",
                "role": "user",
                "content": "Follow-up question",
                "timestamp": time.time() - 3400,
            },
        ]

        # Initialize with previous events
        result = await memory_service.initialize_memory(
            session_id, user_id, recent_events=previous_events
        )
        assert result["event_count"] == 3

        # Continue conversation from where it left off
        new_msg = await memory_service.log_message(session_id, "assistant", "Detailed response")

        # Full history should have all events
        history = await memory_service.get_memory_context(session_id)
        assert len(history) == 4
        assert history[0]["content"] == "First message"
        assert history[3]["content"] == "Detailed response"

    @pytest.mark.asyncio
    async def test_long_conversation_memory_management(self, memory_service):
        """COMPLEX: Manage memory for a long conversation."""
        session_id = "long-conv"
        user_id = "user-789"

        await memory_service.initialize_memory(session_id, user_id)

        # Simulate a long conversation with 20 messages
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            await memory_service.log_message(session_id, role, f"Message {i}")

        # Get summary
        summary = await memory_service.get_session_summary(session_id)
        assert summary["total_events"] == 20
        assert summary["user_messages"] == 10
        assert summary["assistant_messages"] == 10

        # Get last 5 messages
        recent = await memory_service.get_memory_events(session_id, limit=5)
        assert len(recent) == 5
        assert recent[-1]["content"] == "Message 19"


class TestMultiUserSessionManagement:
    """Test multi-user and multi-session scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_sessions_isolation(self, memory_service):
        """COMPLEX: Manage multiple concurrent user sessions without interference."""
        sessions = [
            ("user-1", "conv-1"),
            ("user-2", "conv-2"),
            ("user-3", "conv-3"),
        ]

        # Initialize all sessions
        for user_id, session_id in sessions:
            await memory_service.initialize_memory(session_id, user_id)

        # Add messages to each session
        for user_id, session_id in sessions:
            for i in range(5):
                role = "user" if i % 2 == 0 else "assistant"
                await memory_service.log_message(
                    session_id, role, f"{user_id}-message-{i}", timestamp=time.time() + i
                )

        # Verify isolation
        for user_id, session_id in sessions:
            context = await memory_service.get_memory_context(session_id)
            assert len(context) == 5
            # Verify content belongs to this session
            for event in context:
                assert user_id in event["content"]
                assert event["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_session_cleanup_isolation(self, memory_service):
        """HARD: Cleanup one session without affecting others."""
        await memory_service.log_message("sess-1", "user", "Session 1 message")
        await memory_service.log_message("sess-2", "user", "Session 2 message")
        await memory_service.log_message("sess-3", "user", "Session 3 message")

        # Delete session 2
        result = await memory_service.delete_session_memory("sess-2")
        assert result["deleted_count"] == 1

        # Verify other sessions intact
        assert len(await memory_service.get_memory_context("sess-1")) == 1
        assert len(await memory_service.get_memory_context("sess-2")) == 0
        assert len(await memory_service.get_memory_context("sess-3")) == 1


class TestMemoryTTLAndExpiration:
    """Test TTL and memory expiration scenarios."""

    @pytest.mark.asyncio
    async def test_ttl_expiration_boundary(self, memory_service):
        """HARD: Verify events exactly at and beyond TTL boundary are handled correctly."""
        current_time = time.time()
        session_id = "ttl-test"

        # Add event exactly at TTL boundary (90 days)
        ttl_boundary = current_time - (90 * 86400)
        await memory_service.log_message(
            session_id, "user", "At boundary", timestamp=ttl_boundary + 1
        )

        # Add event beyond TTL
        beyond_ttl = current_time - (91 * 86400)
        await memory_service.log_message(session_id, "user", "Beyond TTL", timestamp=beyond_ttl)

        # Cleanup
        result = await memory_service.clear_old_memory(session_id)

        # The event 1 second after boundary should remain
        # The event beyond boundary should be removed
        context = await memory_service.get_memory_context(session_id)
        assert len(context) == 1
        assert context[0]["content"] == "At boundary"

    @pytest.mark.asyncio
    async def test_memory_expiration_doesnt_delete_session(self, memory_service):
        """COMPLEX: Expiring all events doesn't delete the session."""
        current_time = time.time()
        session_id = "expire-all"

        # Add only old events
        for i in range(3):
            old_time = current_time - (100 * 86400)
            await memory_service.log_message(
                session_id, "user", f"Old event {i}", timestamp=old_time + i
            )

        # Cleanup
        result = await memory_service.clear_old_memory(session_id)
        assert result["removed_count"] == 3
        assert result["remaining_count"] == 0

        # Session should still exist for new messages
        await memory_service.log_message(session_id, "user", "New message")
        context = await memory_service.get_memory_context(session_id)
        assert len(context) == 1


class TestEventOrdering:
    """Test event ordering and timestamp handling."""

    @pytest.mark.asyncio
    async def test_chronological_ordering_preservation(self, memory_service):
        """COMPLEX: Verify events maintain strict chronological order."""
        session_id = "order-test"

        # Add events in intentional non-chronological order
        times = [1000, 1002, 1001, 1003, 1000.5]
        for i, ts in enumerate(times):
            await memory_service.log_message(session_id, "user", f"Event {i}", timestamp=ts)

        # Get ordered context
        context = await memory_service.get_memory_context(session_id)

        # Verify chronological order
        expected_order = [1000, 1000.5, 1001, 1002, 1003]
        actual_order = [event["timestamp"] for event in context]
        assert actual_order == expected_order

    @pytest.mark.asyncio
    async def test_identical_timestamps_preserve_insertion_order(self, memory_service):
        """HARD: When timestamps are identical, insertion order is preserved."""
        session_id = "same-time"
        same_time = 1234567890.0

        # Add events with same timestamp
        for i in range(3):
            await memory_service.log_message(session_id, "user", f"Message {i}", timestamp=same_time)

        context = await memory_service.get_memory_context(session_id)

        # Should maintain insertion order
        assert context[0]["content"] == "Message 0"
        assert context[1]["content"] == "Message 1"
        assert context[2]["content"] == "Message 2"


class TestMemoryDataIntegrity:
    """Test data integrity and consistency."""

    @pytest.mark.asyncio
    async def test_large_content_preservation(self, memory_service):
        """HARD: Preserve large message content (5KB+)."""
        session_id = "large-content"
        large_content = "A" * 5000  # 5KB message

        await memory_service.log_message(session_id, "user", large_content)

        context = await memory_service.get_memory_context(session_id)
        assert context[0]["content"] == large_content
        assert len(context[0]["content"]) == 5000

    @pytest.mark.asyncio
    async def test_unicode_content_preservation(self, memory_service):
        """COMPLEX: Preserve unicode and special characters."""
        session_id = "unicode-test"
        unicode_content = "Hello 世界 🌍 مرحبا мир 🚀"

        await memory_service.log_message(session_id, "user", unicode_content)

        context = await memory_service.get_memory_context(session_id)
        assert context[0]["content"] == unicode_content

    @pytest.mark.asyncio
    async def test_event_id_uniqueness(self, memory_service):
        """COMPLEX: Each event has a unique ID."""
        session_id = "unique-ids"

        event_ids = []
        for i in range(100):
            result = await memory_service.log_message(session_id, "user", f"Message {i}")
            event_ids.append(result["event_id"])

        # All IDs should be unique
        assert len(set(event_ids)) == 100


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_timestamp_handling(self, memory_service):
        """HARD: Handle edge case timestamps (0, negative, very large)."""
        session_id = "timestamp-edge"

        # Zero timestamp
        await memory_service.log_message(session_id, "user", "Zero time", timestamp=0.0)

        # Very large timestamp (far future)
        large_ts = 9999999999.0
        await memory_service.log_message(session_id, "user", "Far future", timestamp=large_ts)

        context = await memory_service.get_memory_context(session_id)
        assert len(context) == 2
        assert context[0]["timestamp"] == 0.0
        assert context[1]["timestamp"] == large_ts

    @pytest.mark.asyncio
    async def test_special_characters_in_session_id(self, memory_service):
        """COMPLEX: Handle special characters in session IDs."""
        session_ids = [
            "sess-with-dashes",
            "sess_with_underscores",
            "sess.with.dots",
            "sess:with:colons",
        ]

        for sess_id in session_ids:
            await memory_service.log_message(sess_id, "user", f"Message for {sess_id}")

        # Verify all were stored separately
        for sess_id in session_ids:
            context = await memory_service.get_memory_context(sess_id)
            assert len(context) == 1
            assert context[0]["session_id"] == sess_id


class TestMemoryConfiguration:
    """Test configuration-related scenarios."""

    @pytest.mark.asyncio
    async def test_config_matches_settings(self, memory_service):
        """BASIC: Verify memory config matches app settings."""
        assert memory_service.memory_type == settings.agent_memory_type
        assert memory_service.retention_days == settings.agent_memory_retention_days

    @pytest.mark.asyncio
    async def test_ttl_calculation_correctness(self, memory_service):
        """BASIC: Verify TTL is correctly calculated from retention days."""
        expected_ttl = settings.agent_memory_retention_days * 86400
        assert memory_service.ttl_seconds == expected_ttl


class TestRealWorldScenarios:
    """Test real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_chat_session_workflow(self, memory_service):
        """COMPLEX: Simulate a real chat session workflow."""
        session_id = "chat-001"
        user_id = "user@example.com"

        # Initialize chat session
        await memory_service.initialize_memory(session_id, user_id)

        # Multi-turn conversation
        conversation = [
            ("user", "What's the weather?"),
            ("assistant", "It's sunny today."),
            ("user", "Any chance of rain?"),
            ("assistant", "No rain expected in the next 48 hours."),
            ("user", "Perfect for a picnic!"),
        ]

        current_time = time.time()
        for i, (role, content) in enumerate(conversation):
            await memory_service.log_message(
                session_id, role, content, timestamp=current_time + i
            )

        # Verify conversation
        context = await memory_service.get_memory_context(session_id)
        assert len(context) == 5

        # Get session summary
        summary = await memory_service.get_session_summary(session_id)
        assert summary["total_events"] == 5
        assert summary["user_messages"] == 3
        assert summary["assistant_messages"] == 2

        # Simulate session recovery
        recovery_result = await memory_service.initialize_memory(session_id, user_id)
        assert recovery_result["event_count"] == 0  # New initialization, no events to load

    @pytest.mark.asyncio
    async def test_multiple_concurrent_conversations(self, memory_service):
        """HARD: Handle multiple concurrent conversations."""
        num_conversations = 5
        messages_per_conv = 10

        # Create multiple conversations
        conversations = []
        for conv_id in range(num_conversations):
            session_id = f"conv-{conv_id}"
            user_id = f"user-{conv_id}"
            await memory_service.initialize_memory(session_id, user_id)

            for msg_id in range(messages_per_conv):
                role = "user" if msg_id % 2 == 0 else "assistant"
                await memory_service.log_message(
                    session_id, role, f"Conv {conv_id} - Message {msg_id}"
                )

            conversations.append((session_id, user_id))

        # Verify all conversations
        for session_id, user_id in conversations:
            context = await memory_service.get_memory_context(session_id)
            assert len(context) == messages_per_conv
            summary = await memory_service.get_session_summary(session_id)
            assert summary["session_id"] == session_id
