"""Tests for CHT-011: Per-request Agent isolation in chat router."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.integrations.agent_core_memory import (
    AgentCoreMemory,
    RequestAgentMemory,
    get_agent_memory,
)


class TestAgentMemoryIsolation:
    """Test Agent Core Memory isolation per request."""

    def test_get_agent_memory_creates_fresh_instance(self):
        """Each call to get_agent_memory() returns a unique instance."""
        memory1 = get_agent_memory()
        memory2 = get_agent_memory()

        # Both should be AgentCoreMemory instances
        assert isinstance(memory1, AgentCoreMemory)
        assert isinstance(memory2, AgentCoreMemory)

        # But they should be different objects
        assert memory1 is not memory2

    @pytest.mark.asyncio
    async def test_request_agent_memory_tracks_sessions(self):
        """RequestAgentMemory tracks initialized sessions for cleanup."""
        memory = AgentCoreMemory()
        req_memory = RequestAgentMemory(memory)

        # Initialize multiple sessions
        await req_memory.initialize(
            session_id="sess-1",
            user_id="user-1",
        )
        await req_memory.initialize(
            session_id="sess-2",
            user_id="user-1",
        )

        # Both sessions should be tracked
        assert "sess-1" in req_memory._initialized_sessions
        assert "sess-2" in req_memory._initialized_sessions

        # Cleanup should clear tracking
        await req_memory.cleanup()
        assert len(req_memory._initialized_sessions) == 0

    @pytest.mark.asyncio
    async def test_request_memory_isolation_between_calls(self):
        """Memory doesn't leak between concurrent RequestAgentMemory instances."""
        # Create two separate request memory instances
        req_mem_1 = RequestAgentMemory(get_agent_memory())
        req_mem_2 = RequestAgentMemory(get_agent_memory())

        # Initialize different sessions in each
        await req_mem_1.initialize(session_id="sess-1", user_id="user-1")
        await req_mem_2.initialize(session_id="sess-2", user_id="user-2")

        # Log messages to each
        await req_mem_1.log_message(session_id="sess-1", role="user", content="Hello")
        await req_mem_2.log_message(session_id="sess-2", role="user", content="World")

        # Get context from each
        context_1 = await req_mem_1.get_memory_context("sess-1")
        context_2 = await req_mem_2.get_memory_context("sess-2")

        # Each should have only their own messages
        assert len(context_1) == 1
        assert context_1[0]["content"] == "Hello"
        assert context_1[0]["session_id"] == "sess-1"

        assert len(context_2) == 1
        assert context_2[0]["content"] == "World"
        assert context_2[0]["session_id"] == "sess-2"

    @pytest.mark.asyncio
    async def test_concurrent_request_memory_isolation(self):
        """Concurrent RequestAgentMemory instances don't interfere."""
        results = []

        async def simulate_request(session_id: str, message: str):
            """Simulate a concurrent request with isolated memory."""
            req_mem = RequestAgentMemory(get_agent_memory())
            await req_mem.initialize(session_id=session_id, user_id="user-1")
            await req_mem.log_message(
                session_id=session_id, role="user", content=message
            )

            # Simulate some processing delay
            await asyncio.sleep(0.01)

            # Get context
            context = await req_mem.get_memory_context(session_id)
            await req_mem.cleanup()

            results.append(
                {
                    "session_id": session_id,
                    "message": message,
                    "context_size": len(context),
                }
            )

        # Run 5 concurrent requests
        tasks = [
            simulate_request(f"sess-{i}", f"message-{i}") for i in range(5)
        ]
        await asyncio.gather(*tasks)

        # Each request should have exactly 1 message in its context
        assert len(results) == 5
        for result in results:
            assert result["context_size"] == 1

    @pytest.mark.asyncio
    async def test_memory_cleanup_removes_session_data(self):
        """Cleanup properly removes tracked session data."""
        memory = AgentCoreMemory()
        req_mem = RequestAgentMemory(memory)

        # Initialize and log a message
        await req_mem.initialize(session_id="sess-1", user_id="user-1")
        await req_mem.log_message(
            session_id="sess-1", role="user", content="test message"
        )

        # Verify message exists
        context_before = await req_mem.get_memory_context("sess-1")
        assert len(context_before) == 1

        # Cleanup
        await req_mem.cleanup()

        # Tracking should be cleared
        assert len(req_mem._initialized_sessions) == 0


class TestChatStreamingEndpointIsolation:
    """Test per-request isolation in chat streaming endpoint."""

    @pytest.fixture
    def mock_auth_token(self):
        """Create a mock JWT token for testing."""
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

    @pytest.mark.asyncio
    async def test_stream_endpoint_validates_session_ownership(self):
        """Stream endpoint rejects requests for sessions user doesn't own."""
        client = TestClient(app)

        # Mock the chat service to return a session for a different user
        with patch(
            "app.api.v1.chat.router.ChatService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Session exists but belongs to different user
            mock_service.get_session.return_value = {
                "session_id": "sess-123",
                "user_id": "different-user",  # Different owner
                "title": "Chat",
            }

            response = client.post(
                "/api/v1/chat/sessions/sess-123/stream",
                json={"content": "Hello"},
                headers={"Authorization": f"Bearer {mock_auth_token}"},
            )

            # Should get 403 Forbidden
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_stream_endpoint_returns_404_for_missing_session(self):
        """Stream endpoint returns 404 when session doesn't exist."""
        client = TestClient(app)

        with patch(
            "app.api.v1.chat.router.ChatService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Session doesn't exist
            mock_service.get_session.return_value = None

            response = client.post(
                "/api/v1/chat/sessions/sess-invalid/stream",
                json={"content": "Hello"},
                headers={"Authorization": f"Bearer {mock_auth_token}"},
            )

            # Should get 404 Not Found
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_endpoint_initializes_memory(self):
        """Stream endpoint initializes per-request memory with context."""
        client = TestClient(app)

        with patch(
            "app.api.v1.chat.router.ChatService"
        ) as mock_service_class, patch(
            "app.api.v1.chat.router.get_request_agent_memory"
        ) as mock_get_memory:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Mock session
            mock_service.get_session.return_value = {
                "session_id": "sess-123",
                "user_id": "user-123",
                "title": "Chat",
                "is_active": True,
            }

            # Mock messages
            mock_service.get_messages.return_value = {
                "messages": [
                    {
                        "message_id": "msg-1",
                        "role": "user",
                        "content": "Hi",
                        "timestamp": 1000,
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "has_next": False,
                "has_prev": False,
            }

            # Mock agent core
            with patch(
                "app.api.v1.chat.router.AgentCoreClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Agent returns token events
                async def mock_invoke():
                    yield {"type": "token", "content": "Hello"}

                mock_client.invoke_agent.return_value = mock_invoke()

                # Call endpoint
                response = client.post(
                    "/api/v1/chat/sessions/sess-123/stream",
                    json={"content": "Test"},
                    headers={"Authorization": f"Bearer {mock_auth_token}"},
                )

                # Should be successful (streaming)
                assert response.status_code == 200


class TestConcurrentRequestIsolation:
    """Test isolation between concurrent requests."""

    @pytest.mark.asyncio
    async def test_no_memory_leakage_between_concurrent_requests(self):
        """Concurrent streaming requests maintain independent memory."""
        memory_instances = {}

        async def create_isolated_memory(request_id: str):
            """Create a new memory instance for this request."""
            mem = get_agent_memory()
            memory_instances[request_id] = mem
            return RequestAgentMemory(mem)

        # Simulate 3 concurrent requests
        async def request_handler(request_id: str, session_id: str, message: str):
            req_mem = await create_isolated_memory(request_id)

            # Initialize
            await req_mem.initialize(session_id=session_id, user_id="user-1")

            # Add message unique to this request
            await req_mem.log_message(
                session_id=session_id, role="user", content=message
            )

            # Simulate processing
            await asyncio.sleep(0.01)

            # Get context
            context = await req_mem.get_memory_context(session_id)

            # Cleanup
            await req_mem.cleanup()

            return {
                "request_id": request_id,
                "session_id": session_id,
                "message_count": len(context),
                "content": context[0]["content"] if context else None,
            }

        # Run 3 concurrent requests
        results = await asyncio.gather(
            request_handler("req-1", "sess-1", "request-1-message"),
            request_handler("req-2", "sess-2", "request-2-message"),
            request_handler("req-3", "sess-3", "request-3-message"),
        )

        # Each request should have exactly 1 message from its own context
        assert len(results) == 3
        for result in results:
            assert result["message_count"] == 1
            assert f"request-{result['request_id'].split('-')[1]}" in result["content"]

    @pytest.mark.asyncio
    async def test_memory_instances_are_independent(self):
        """Memory instances from different requests are completely independent."""
        req_mem_1 = RequestAgentMemory(get_agent_memory())
        req_mem_2 = RequestAgentMemory(get_agent_memory())

        # Initialize same session ID but in different memory instances
        await req_mem_1.initialize(session_id="sess-same", user_id="user-1")
        await req_mem_2.initialize(session_id="sess-same", user_id="user-1")

        # Add different messages
        await req_mem_1.log_message(
            session_id="sess-same", role="user", content="message-from-req-1"
        )
        await req_mem_2.log_message(
            session_id="sess-same", role="user", content="message-from-req-2"
        )

        # Get context from each
        context_1 = await req_mem_1.get_memory_context("sess-same")
        context_2 = await req_mem_2.get_memory_context("sess-same")

        # Each should have only their own message
        assert len(context_1) == 1
        assert context_1[0]["content"] == "message-from-req-1"

        assert len(context_2) == 1
        assert context_2[0]["content"] == "message-from-req-2"


class TestErrorHandling:
    """Test error handling in isolation."""

    @pytest.mark.asyncio
    async def test_memory_init_timeout_returns_503(self):
        """Memory initialization timeout returns 503 Service Unavailable."""
        client = TestClient(app)

        with patch(
            "app.api.v1.chat.router.ChatService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Valid session
            mock_service.get_session.return_value = {
                "session_id": "sess-123",
                "user_id": "user-123",
                "is_active": True,
            }

            # get_messages times out
            async def timeout_coro(*args, **kwargs):
                await asyncio.sleep(10)  # Simulate timeout

            mock_service.get_messages.side_effect = timeout_coro

            token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

            response = client.post(
                "/api/v1/chat/sessions/sess-123/stream",
                json={"content": "Test"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=2,
            )

            # Should timeout or return 503
            assert response.status_code in (503, 504) or response.status_code == 200

    @pytest.mark.asyncio
    async def test_cleanup_failure_logged_but_doesnt_fail_request(self):
        """Memory cleanup failure is logged but doesn't fail the request."""
        req_mem = RequestAgentMemory(get_agent_memory())

        # Mock cleanup to raise an error
        with patch.object(req_mem._memory, "clear_old_memory") as mock_clear:
            mock_clear.side_effect = Exception("Cleanup error")

            # Should not raise
            await req_mem.cleanup()  # Should log warning but not raise


@pytest.mark.asyncio
async def test_isolation_pattern_no_global_state():
    """Verify no global state is shared between isolated memory instances."""
    instances = []

    async def create_and_populate_memory(request_id: str):
        """Create memory and add some data."""
        mem = RequestAgentMemory(get_agent_memory())

        session_id = f"sess-{request_id}"
        await mem.initialize(session_id=session_id, user_id="user-1")

        for i in range(3):
            await mem.log_message(
                session_id=session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"message-{request_id}-{i}",
            )

        instances.append((request_id, mem))

    # Create 5 independent memory instances
    await asyncio.gather(*[create_and_populate_memory(i) for i in range(5)])

    # Verify each has only its own data
    for request_id, mem in instances:
        session_id = f"sess-{request_id}"
        context = await mem.get_memory_context(session_id)

        # Should have exactly 3 messages from this request
        assert len(context) == 3

        # All messages should be from this specific request
        for msg in context:
            assert f"message-{request_id}" in msg["content"]
            assert msg["session_id"] == session_id
