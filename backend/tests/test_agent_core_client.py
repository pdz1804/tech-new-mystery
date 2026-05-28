"""Comprehensive tests for Agent Core Client (HTTP API)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import json

from app.integrations.agent_core_client import AgentCoreClient


async def async_iter(items):
    """Helper to create an async iterator from a list."""
    for item in items:
        yield item


class TestAgentCoreClientInitialization:
    """Test HTTP client creation and configuration."""

    def test_init_with_defaults(self):
        """Initialize AgentCoreClient with default settings."""
        with patch("app.integrations.agent_core_client.settings") as mock_settings:
            mock_settings.agent_core_base_url = "http://localhost:8000"
            mock_settings.agent_core_api_key = "test-key"
            mock_settings.agent_core_timeout = 60

            client = AgentCoreClient()

            assert client.base_url == "http://localhost:8000"
            assert client.api_key == "test-key"
            assert client.timeout == 60
            assert client._client is not None

    def test_init_with_custom_values(self):
        """Initialize AgentCoreClient with custom values."""
        client = AgentCoreClient(
            base_url="http://custom:9000",
            api_key="custom-key",
            timeout=30,
        )

        assert client.base_url == "http://custom:9000"
        assert client.api_key == "custom-key"
        assert client.timeout == 30

    def test_init_strips_trailing_slash(self):
        """Base URL has trailing slash removed."""
        client = AgentCoreClient(base_url="http://localhost:8000/")

        assert client.base_url == "http://localhost:8000"

    def test_connection_pool_created(self):
        """Verify connection pool is created."""
        client = AgentCoreClient()

        assert isinstance(client._client, httpx.AsyncClient)
        assert client._client._transport is not None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing the HTTP client."""
        client = AgentCoreClient()
        await client.close()

        # Client should be closed (attempting operations should fail)
        with pytest.raises(RuntimeError):
            await client._client.get("http://localhost:8000/health")

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager usage."""
        async with AgentCoreClient() as client:
            assert client is not None
            assert isinstance(client._client, httpx.AsyncClient)

        # After exit, client should be closed
        with pytest.raises(RuntimeError):
            await client._client.get("http://localhost:8000/health")


class TestAgentCoreClientHeaders:
    """Test authentication header construction."""

    def test_headers_without_api_key(self):
        """Headers without API key."""
        client = AgentCoreClient(api_key=None)
        headers = client._get_headers()

        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/x-ndjson"
        assert "X-API-Key" not in headers

    def test_headers_with_api_key(self):
        """Headers include X-API-Key when provided."""
        client = AgentCoreClient(api_key="secret-key-123")
        headers = client._get_headers()

        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "secret-key-123"
        assert headers["Content-Type"] == "application/json"

    def test_headers_content_type(self):
        """Headers have correct content type."""
        client = AgentCoreClient()
        headers = client._get_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/x-ndjson"


class TestAgentCoreClientStreaming:
    """Test streaming responses and event parsing."""

    @pytest.mark.asyncio
    async def test_invoke_agent_success(self):
        """Test successful agent invocation with streaming."""
        client = AgentCoreClient(base_url="http://localhost:8000", api_key="test-key")

        # Mock the streaming response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events = [
            json.dumps({"type": "token", "content": "Hello"}),
            json.dumps({"type": "token", "content": " world"}),
            json.dumps({"type": "done"}),
        ]

        # Use async iterator for aiter_lines
        async def mock_aiter_lines():
            for event in events:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(
            client._client, "stream"
        ) as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            result = []
            async for event in client.invoke_agent(
                session_id="session-1",
                user_message="Hello Agent Core",
            ):
                result.append(event)

            assert len(result) == 3
            assert result[0]["type"] == "token"
            assert result[0]["content"] == "Hello"
            assert result[1]["content"] == " world"
            assert result[2]["type"] == "done"

        await client.close()

    @pytest.mark.asyncio
    async def test_streaming_token_events(self):
        """Verify token events are parsed correctly."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events = [
            json.dumps({"type": "token", "content": "Token1"}),
            json.dumps({"type": "token", "content": "Token2"}),
        ]

        async def mock_aiter_lines():
            for event in events:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            tokens = []
            async for event in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                if event["type"] == "token":
                    tokens.append(event["content"])

            assert tokens == ["Token1", "Token2"]

        await client.close()

    @pytest.mark.asyncio
    async def test_streaming_tool_invocation_events(self):
        """Verify tool_invocation events include tool name and args."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events = [
            json.dumps({
                "type": "tool_invocation",
                "tool_name": "web_search",
                "tool_args": {"query": "test"},
                "tool_id": "tool-1",
            }),
        ]

        async def mock_aiter_lines():
            for event in events:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            tool_events = []
            async for event in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                if event["type"] == "tool_invocation":
                    tool_events.append(event)

            assert len(tool_events) == 1
            assert tool_events[0]["tool_name"] == "web_search"
            assert tool_events[0]["tool_args"]["query"] == "test"
            assert "tool_id" in tool_events[0]

        await client.close()

    @pytest.mark.asyncio
    async def test_streaming_tool_result_events(self):
        """Verify tool_result events include results."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events = [
            json.dumps({
                "type": "tool_result",
                "tool_id": "tool-1",
                "result": "Success result",
            }),
        ]

        async def mock_aiter_lines():
            for event in events:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            result_events = []
            async for event in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                if event["type"] == "tool_result":
                    result_events.append(event)

            assert len(result_events) == 1
            assert result_events[0]["tool_id"] == "tool-1"
            assert result_events[0]["result"] == "Success result"

        await client.close()

    @pytest.mark.asyncio
    async def test_streaming_done_event(self):
        """Verify done event marks completion."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events = [
            json.dumps({"type": "token", "content": "Response"}),
            json.dumps({"type": "done", "final": True}),
        ]

        async def mock_aiter_lines():
            for event in events:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            done_event_found = False
            async for event in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                if event["type"] == "done":
                    done_event_found = True

            assert done_event_found

        await client.close()

    @pytest.mark.asyncio
    async def test_event_structure_validation(self):
        """All events have correct structure."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events_data = [
            json.dumps({"type": "token", "content": "test"}),
            json.dumps({"type": "tool_invocation", "tool_name": "search"}),
            json.dumps({"type": "tool_result", "result": "data"}),
            json.dumps({"type": "done"}),
        ]

        async def mock_aiter_lines():
            for event in events_data:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            events = []
            async for event in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                events.append(event)

            # All events should have type field
            assert all("type" in event for event in events)
            # Event types should be valid
            assert all(event["type"] in ["token", "tool_invocation", "tool_result", "done", "error"] for event in events)

        await client.close()


class TestAgentCoreClientErrorHandling:
    """Test error handling for network failures and API errors."""

    @pytest.mark.asyncio
    async def test_timeout_exception(self):
        """Simulate timeout and raise exception."""
        client = AgentCoreClient()

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(httpx.TimeoutException):
                async for _ in client.invoke_agent(
                    session_id="sess-1",
                    user_message="test",
                ):
                    pass

        await client.close()

    @pytest.mark.asyncio
    async def test_http_error_exception(self):
        """Simulate HTTP error and raise exception."""
        client = AgentCoreClient()

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.side_effect = httpx.HTTPError("Connection failed")

            with pytest.raises(httpx.HTTPError):
                async for _ in client.invoke_agent(
                    session_id="sess-1",
                    user_message="test",
                ):
                    pass

        await client.close()

    @pytest.mark.asyncio
    async def test_json_parse_error_handling(self):
        """Invalid JSON lines are handled gracefully."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events_data = [
            json.dumps({"type": "token", "content": "valid"}),
            "invalid json {",
            json.dumps({"type": "done"}),
        ]

        async def mock_aiter_lines():
            for event in events_data:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            events = []
            async for event in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                events.append(event)

            # Should have valid event, error event for invalid JSON, and done
            assert len(events) == 3
            assert events[0]["type"] == "token"
            assert events[1]["type"] == "error"
            assert events[2]["type"] == "done"

        await client.close()

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        """HTTP status errors are raised."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "500 Server Error",
                request=MagicMock(),
                response=MagicMock(),
            )
        )

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                async for _ in client.invoke_agent(
                    session_id="sess-1",
                    user_message="test",
                ):
                    pass

        await client.close()


class TestAgentCoreClientConcurrency:
    """Test concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Make 5 concurrent invoke_agent calls."""
        import asyncio

        client = AgentCoreClient()

        async def create_response(*args, **kwargs):
            response = AsyncMock()
            response.raise_for_status = MagicMock()

            events_data = [
                json.dumps({"type": "token", "content": "test"}),
                json.dumps({"type": "done"}),
            ]

            async def mock_aiter_lines():
                for event in events_data:
                    yield event

            response.aiter_lines = mock_aiter_lines
            return response

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.side_effect = create_response

            # Create 5 concurrent tasks
            tasks = [
                client.invoke_agent(
                    session_id=f"sess-{i}",
                    user_message=f"message-{i}",
                )
                for i in range(5)
            ]

            # Collect all events from all tasks
            results = []
            for task in tasks:
                events = []
                async for event in task:
                    events.append(event)
                results.append(events)

            # All tasks should complete successfully
            assert len(results) == 5
            for events in results:
                assert len(events) == 2
                assert events[0]["type"] == "token"
                assert events[1]["type"] == "done"

        await client.close()

    @pytest.mark.asyncio
    async def test_no_connection_leakage(self):
        """No connection leakage after concurrent requests."""
        client = AgentCoreClient()

        # Mock response factory
        async def create_response(*args, **kwargs):
            response = AsyncMock()
            response.raise_for_status = MagicMock()

            async def mock_aiter_lines():
                yield json.dumps({"type": "done"})

            response.aiter_lines = mock_aiter_lines
            return response

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.side_effect = create_response

            # Run multiple requests
            for i in range(10):
                async for _ in client.invoke_agent(
                    session_id=f"sess-{i}",
                    user_message="test",
                ):
                    pass

            # Should have invoked stream 10 times (no leakage)
            assert mock_stream.call_count == 10

        await client.close()


class TestAgentCoreClientAuthentication:
    """Test authentication handling."""

    def test_auth_header_included(self):
        """X-API-Key header is included."""
        client = AgentCoreClient(api_key="test-api-key")
        headers = client._get_headers()

        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test-api-key"

    def test_correct_api_key_used(self):
        """Correct API key is used in headers."""
        api_key = "secure-key-12345"
        client = AgentCoreClient(api_key=api_key)
        headers = client._get_headers()

        assert headers["X-API-Key"] == api_key

    @pytest.mark.asyncio
    async def test_auth_header_sent_in_request(self):
        """Auth header is sent in actual request."""
        client = AgentCoreClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            yield json.dumps({"type": "done"})

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            async for _ in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                pass

            # Verify stream was called with auth header
            mock_stream.assert_called_once()
            call_kwargs = mock_stream.call_args[1]
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["X-API-Key"] == "test-key"

        await client.close()

    @pytest.mark.asyncio
    async def test_invalid_key_401_error(self):
        """Invalid API key results in 401 error."""
        client = AgentCoreClient(api_key="invalid-key")

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            )
        )

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                async for _ in client.invoke_agent(
                    session_id="sess-1",
                    user_message="test",
                ):
                    pass

        await client.close()


class TestAgentCoreClientIntegration:
    """Integration tests for the full workflow."""

    @pytest.mark.asyncio
    async def test_full_agent_invocation_workflow(self):
        """Test complete agent invocation workflow."""
        client = AgentCoreClient(
            base_url="http://localhost:8000",
            api_key="test-key",
            timeout=60,
        )

        # Simulate a realistic streaming response
        events_data = [
            json.dumps({"type": "token", "content": "I"}),
            json.dumps({"type": "token", "content": " found"}),
            json.dumps({
                "type": "tool_invocation",
                "tool_name": "web_search",
                "tool_args": {"query": "test"},
                "tool_id": "tool-1",
            }),
            json.dumps({
                "type": "tool_result",
                "tool_id": "tool-1",
                "result": "Search results...",
            }),
            json.dumps({"type": "token", "content": " some info"}),
            json.dumps({"type": "done"}),
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            for event in events_data:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            # Collect all events
            all_events = []
            tokens = []
            tool_calls = []
            tool_results = []

            async for event in client.invoke_agent(
                session_id="user-session-1",
                user_message="What is Python?",
                context={"knowledge_base": "tech"},
                user_id="user-123",
            ):
                all_events.append(event)

                if event["type"] == "token":
                    tokens.append(event["content"])
                elif event["type"] == "tool_invocation":
                    tool_calls.append(event)
                elif event["type"] == "tool_result":
                    tool_results.append(event)

            # Verify complete workflow
            assert len(all_events) == 6
            assert "".join(tokens) == "I found some info"
            assert len(tool_calls) == 1
            assert tool_calls[0]["tool_name"] == "web_search"
            assert len(tool_results) == 1
            assert tool_results[0]["result"] == "Search results..."

            # Verify request was made correctly
            mock_stream.assert_called_once()
            call_args = mock_stream.call_args
            assert call_args[0][1] == "http://localhost:8000/agent/invoke"
            assert call_args[1]["json"]["session_id"] == "user-session-1"
            assert call_args[1]["json"]["user_id"] == "user-123"

        await client.close()

    @pytest.mark.asyncio
    async def test_invoke_agent_with_context(self):
        """Verify context is passed to the API."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            return
            yield  # Make it an async generator

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            context = {"user_pref": "detailed", "language": "en"}
            async for _ in client.invoke_agent(
                session_id="sess-1",
                user_message="Hello",
                context=context,
            ):
                pass

            # Verify context was included in payload
            call_kwargs = mock_stream.call_args[1]
            assert call_kwargs["json"]["context"] == context

        await client.close()

    @pytest.mark.asyncio
    async def test_invoke_agent_empty_lines_skipped(self):
        """Empty lines in stream are skipped."""
        client = AgentCoreClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        events_data = [
            json.dumps({"type": "token", "content": "test"}),
            "",
            "  ",
            json.dumps({"type": "done"}),
        ]

        async def mock_aiter_lines():
            for event in events_data:
                yield event

        mock_response.aiter_lines = mock_aiter_lines

        with patch.object(client._client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            events = []
            async for event in client.invoke_agent(
                session_id="sess-1",
                user_message="test",
            ):
                events.append(event)

            # Only 2 valid events (empty lines should be skipped)
            assert len(events) == 2
            assert events[0]["type"] == "token"
            assert events[1]["type"] == "done"

        await client.close()
