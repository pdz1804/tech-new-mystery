"""
TASK-CHT-004 Validation Tests: Agent Core Memory Configuration

Tests validate correct implementation of per-request isolation and memory
configuration WITHOUT singleton patterns.

Test Coverage:
1. Agent Core SDK initialization (config verification)
2. Memory context on init (loading recent events)
3. Message logging to Agent Core (persistence)
4. Per-request isolation (no singleton, no cross-contamination)
5. TTL validation (90-day retention)
"""

import pytest
import time
from app.integrations.agent_core_memory import AgentCoreMemory, get_agent_memory
from app.config import settings


class TestAgentCoreMemoryConfiguration:
    """Test 1: Agent Core SDK initialization with correct configuration."""

    def test_memory_type_is_short_term(self):
        """PASS: Memory type configured as SHORT_TERM."""
        memory = get_agent_memory()
        assert memory.memory_type == "SHORT_TERM"
        assert memory.memory_type == settings.agent_memory_type

    def test_retention_days_is_90(self):
        """PASS: Retention configured for 90 days."""
        memory = get_agent_memory()
        assert memory.retention_days == 90
        assert memory.retention_days == settings.agent_memory_retention_days

    def test_ttl_seconds_calculated_correctly(self):
        """PASS: TTL seconds = 90 days * 86400 seconds/day."""
        memory = get_agent_memory()
        expected_ttl = 90 * 86400
        assert memory.ttl_seconds == expected_ttl


class TestMemoryContextOnInit:
    """Test 2: Load recent conversation context from memory on initialization."""

    @pytest.mark.asyncio
    async def test_initialize_with_empty_context(self):
        """PASS: Initialize fresh session with no prior context."""
        memory = get_agent_memory()
        result = await memory.initialize_memory("sess-001", "user-123")

        assert result["status"] == "initialized"
        assert result["session_id"] == "sess-001"
        assert result["user_id"] == "user-123"
        assert result["event_count"] == 0

    @pytest.mark.asyncio
    async def test_initialize_with_recent_events(self):
        """PASS: Load recent conversation context from Agent Core memory on init."""
        memory = get_agent_memory()

        # Simulate loading 5 recent events from Agent Core (like DynamoDB)
        recent_events = [
            {
                "event_id": f"evt-{i}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Previous message {i}",
                "timestamp": time.time() - (10 - i),
            }
            for i in range(5)
        ]

        result = await memory.initialize_memory(
            "sess-002", "user-456", recent_events=recent_events
        )

        assert result["status"] == "initialized"
        assert result["event_count"] == 5
        assert result["memory_type"] == "SHORT_TERM"

        # Verify events were loaded
        context = await memory.get_memory_context("sess-002")
        assert len(context) == 5

    @pytest.mark.asyncio
    async def test_loaded_events_maintain_structure(self):
        """PASS: Verify loaded events have correct Agent Core structure."""
        memory = get_agent_memory()

        recent_events = [
            {
                "event_id": "evt-1",
                "role": "user",
                "content": "What is AI?",
                "timestamp": time.time() - 100,
            },
            {
                "event_id": "evt-2",
                "role": "assistant",
                "content": "AI is artificial intelligence.",
                "timestamp": time.time() - 50,
            },
        ]

        await memory.initialize_memory("sess-003", "user-789", recent_events=recent_events)
        context = await memory.get_memory_context("sess-003")

        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "What is AI?"
        assert context[1]["role"] == "assistant"
        assert context[1]["content"] == "AI is artificial intelligence."


class TestMessageLoggingToAgentCore:
    """Test 3: Log messages to Agent Core memory during conversation."""

    @pytest.mark.asyncio
    async def test_log_user_message(self):
        """PASS: Log user message to Agent Core memory."""
        memory = get_agent_memory()
        await memory.initialize_memory("sess-100", "user-001")

        result = await memory.log_message("sess-100", "user", "Hello Agent Core")

        assert result["status"] == "logged"
        assert result["role"] == "user"
        assert "event_id" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_log_assistant_message(self):
        """PASS: Log assistant message to Agent Core memory."""
        memory = get_agent_memory()
        await memory.initialize_memory("sess-101", "user-002")

        result = await memory.log_message("sess-101", "assistant", "Hello user")

        assert result["status"] == "logged"
        assert result["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_multi_turn_context_preserved(self):
        """PASS: Verify multi-turn context is preserved in Agent Core."""
        memory = get_agent_memory()
        await memory.initialize_memory("sess-102", "user-003")

        # Simulate multi-turn conversation
        conversation = [
            ("user", "What is agent core memory?"),
            ("assistant", "It stores conversation context."),
            ("user", "How long is it retained?"),
            ("assistant", "90 days by default."),
        ]

        for role, content in conversation:
            await memory.log_message("sess-102", role, content)

        context = await memory.get_memory_context("sess-102")
        assert len(context) == 4

        # Verify all messages are in context
        contents = [e["content"] for e in context]
        for _, content in conversation:
            assert content in contents


class TestPerRequestIsolation:
    """Test 4: Per-request isolation without singleton pattern."""

    def test_each_call_creates_fresh_instance(self):
        """PASS: get_agent_memory() returns new instance each time."""
        mem1 = get_agent_memory()
        mem2 = get_agent_memory()
        mem3 = get_agent_memory()

        # All should be different instances (no singleton)
        assert mem1 is not mem2
        assert mem2 is not mem3
        assert mem1 is not mem3

    def test_no_state_leakage_between_requests(self):
        """PASS: Different request instances have isolated state."""
        mem_req1 = get_agent_memory()
        mem_req2 = get_agent_memory()

        # Request 1 adds data
        mem_req1._memory_store["sess-req1"] = []

        # Request 2 should not have this data
        assert "sess-req1" not in mem_req2._memory_store

    @pytest.mark.asyncio
    async def test_concurrent_requests_no_contamination(self):
        """PASS: Two concurrent requests don't contaminate each other."""
        # Simulate Request 1
        mem_r1 = get_agent_memory()
        await mem_r1.initialize_memory("sess-req1", "user-r1")
        await mem_r1.log_message("sess-req1", "user", "Request 1 message")

        # Simulate Request 2 (concurrent)
        mem_r2 = get_agent_memory()
        await mem_r2.initialize_memory("sess-req2", "user-r2")
        await mem_r2.log_message("sess-req2", "user", "Request 2 message")

        # Verify isolation
        context_r1 = await mem_r1.get_memory_context("sess-req1")
        context_r2 = await mem_r2.get_memory_context("sess-req2")

        # Request 1 only has its own message
        assert len(context_r1) == 1
        assert context_r1[0]["content"] == "Request 1 message"

        # Request 2 only has its own message
        assert len(context_r2) == 1
        assert context_r2[0]["content"] == "Request 2 message"

        # Request 2 cannot see Request 1's session
        req2_context_r1 = await mem_r2.get_memory_context("sess-req1")
        assert len(req2_context_r1) == 0


class TestTTLValidation:
    """Test 5: TTL validation and 90-day retention configuration."""

    def test_ttl_set_to_90_days(self):
        """PASS: TTL configured for 90-day retention."""
        memory = get_agent_memory()
        expected_seconds = 90 * 86400
        assert memory.ttl_seconds == expected_seconds

    @pytest.mark.asyncio
    async def test_old_messages_expired_beyond_90_days(self):
        """PASS: Messages older than 90 days are expired."""
        memory = get_agent_memory()

        current_time = time.time()
        old_time = current_time - (100 * 86400)  # 100 days old
        recent_time = current_time - (30 * 86400)  # 30 days old

        # Add old message
        await memory.log_message("sess-200", "user", "Very old", timestamp=old_time)
        # Add recent message
        await memory.log_message("sess-200", "user", "Recent", timestamp=recent_time)

        # Clear old memory
        await memory.clear_old_memory("sess-200")

        # Only recent message should remain
        context = await memory.get_memory_context("sess-200")
        assert len(context) == 1
        assert context[0]["content"] == "Recent"

    @pytest.mark.asyncio
    async def test_retention_days_matches_config(self):
        """PASS: Retention days matches Agent Core config."""
        memory = get_agent_memory()
        assert memory.retention_days == settings.agent_memory_retention_days
        assert settings.agent_memory_retention_days == 90


class TestConfigurationIntegration:
    """Verify Agent Core config is properly integrated."""

    def test_config_agent_memory_type_correct(self):
        """PASS: Config has correct agent memory type."""
        assert settings.agent_memory_type == "SHORT_TERM"

    def test_config_retention_days_correct(self):
        """PASS: Config has correct retention days."""
        assert settings.agent_memory_retention_days == 90

    @pytest.mark.asyncio
    async def test_memory_respects_config(self):
        """PASS: AgentCoreMemory respects Agent Core config settings."""
        memory = get_agent_memory()

        assert memory.memory_type == settings.agent_memory_type
        assert memory.retention_days == settings.agent_memory_retention_days
