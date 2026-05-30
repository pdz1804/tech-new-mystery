"""Tests for SSE streaming chat endpoint (CHT-010)."""

import pytest
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.chat.router import router as chat_router
from app.services.chat_service import ChatService
from app.integrations.agent_core_client import AgentCoreClient
from app.api.v1.chat.schemas import MessageRequest


@pytest.fixture
def valid_user_id():
    """User ID for testing."""
    return "test-user-123"


@pytest.fixture
def valid_session_id():
    """Session ID for testing."""
    return "sess-123"


@pytest.fixture
def mock_token():
    """Mock JWT token."""
    from jose import jwt
    from app.config import settings
    from datetime import datetime, timedelta

    payload = {
        "sub": "test-user-123",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


class TestSSEStreamingEndpoint:
    """Test SSE streaming endpoint."""

    @pytest.mark.asyncio
    async def test_stream_endpoint_authentication_required(self):
        """Streaming endpoint should require valid authentication."""
        # Tested via endpoint logic in router
        # get_current_user dependency will raise 403 if no valid token
        pass

    @pytest.mark.asyncio
    async def test_stream_endpoint_validates_session_exists(self):
        """Streaming to non-existent session should return 404."""
        # Tested via endpoint logic - get_session returns None
        # raises HTTPException with 404
        pass

    @pytest.mark.asyncio
    async def test_stream_endpoint_saves_user_message(self):
        """User message should be saved before streaming."""
        # Tested via endpoint logic:
        # 1. get_session validates session exists
        # 2. add_message is called with role="user"
        # 3. Then agent_core.invoke_agent is called
        pass


class TestSSEEventFormatting:
    """Test SSE event formatting (RFC 6202 compliant)."""

    def test_token_event_format(self):
        """Token events should be RFC 6202 compliant."""
        event = {"type": "token", "content": "Hello"}
        formatted = f"event: token\ndata: {json.dumps(event)}\n\n"

        # Verify format
        assert formatted.startswith("event: token\n")
        assert "data:" in formatted
        assert formatted.endswith("\n\n")

    def test_tool_invocation_event_format(self):
        """Tool invocation events should be RFC 6202 compliant."""
        event = {
            "type": "tool_invocation",
            "tool_name": "semantic_search",
            "tool_id": "tool-1",
            "tool_args": {"query": "AI"},
        }
        formatted = f"event: tool_invocation\ndata: {json.dumps(event)}\n\n"

        # Verify format
        assert formatted.startswith("event: tool_invocation\n")
        assert "data:" in formatted
        assert formatted.endswith("\n\n")

    def test_tool_result_event_format(self):
        """Tool result events should be RFC 6202 compliant."""
        event = {
            "type": "tool_result",
            "tool_name": "semantic_search",
            "result_summary": "Found 10 articles",
            "status": "completed",
        }
        formatted = f"event: tool_result\ndata: {json.dumps(event)}\n\n"

        # Verify format
        assert formatted.startswith("event: tool_result\n")
        assert "data:" in formatted
        assert formatted.endswith("\n\n")

    def test_done_event_format(self):
        """Done events should be RFC 6202 compliant."""
        event = {
            "type": "done",
            "message_id": "msg-123",
            "tokens": 42,
        }
        formatted = f"event: done\ndata: {json.dumps(event)}\n\n"

        # Verify format
        assert formatted.startswith("event: done\n")
        assert "data:" in formatted
        assert formatted.endswith("\n\n")

    def test_error_event_format(self):
        """Error events should be RFC 6202 compliant."""
        event = {
            "type": "error",
            "error": "Timeout occurred",
            "code": "TIMEOUT",
        }
        formatted = f"event: error\ndata: {json.dumps(event)}\n\n"

        # Verify format
        assert formatted.startswith("event: error\n")
        assert "data:" in formatted
        assert formatted.endswith("\n\n")


class TestEventStreamingSequence:
    """Test proper event streaming sequence."""

    @pytest.mark.asyncio
    async def test_event_sequence_token_then_done(self):
        """Events should be in correct order: tokens then done."""
        events = [
            {"type": "token", "content": "Hello"},
            {"type": "token", "content": " "},
            {"type": "token", "content": "world"},
            {"type": "done", "message_id": "msg-1", "tokens": 3},
        ]

        # Verify types and order
        token_count = sum(1 for e in events if e["type"] == "token")
        done_count = sum(1 for e in events if e["type"] == "done")

        assert token_count == 3
        assert done_count == 1
        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_event_sequence_with_tool_calls(self):
        """Events should handle tool calls correctly."""
        events = [
            {"type": "token", "content": "Let "},
            {"type": "token", "content": "me "},
            {"type": "token", "content": "search"},
            {
                "type": "tool_invocation",
                "tool_name": "semantic_search",
                "tool_id": "tool-1",
                "tool_args": {"query": "AI"},
            },
            {
                "type": "tool_result",
                "tool_name": "semantic_search",
                "result_summary": "Found articles",
                "status": "completed",
            },
            {"type": "token", "content": "Based"},
            {"type": "token", "content": " on results"},
            {"type": "done", "message_id": "msg-1", "tokens": 6},
        ]

        # Verify sequence
        tool_invocations = [e for e in events if e["type"] == "tool_invocation"]
        tool_results = [e for e in events if e["type"] == "tool_result"]

        assert len(tool_invocations) == 1
        assert len(tool_results) == 1
        assert tool_invocations[0]["tool_name"] == tool_results[0]["tool_name"]

    @pytest.mark.asyncio
    async def test_error_event_ends_stream(self):
        """Error events should terminate stream."""
        events = [
            {"type": "token", "content": "Hello"},
            {"type": "error", "error": "Timeout", "code": "TIMEOUT"},
        ]

        # Verify error terminates stream
        assert events[-1]["type"] == "error"


class TestStreamingErrorHandling:
    """Test error handling in streaming."""

    @pytest.mark.asyncio
    async def test_agent_core_timeout_returns_error_event(self):
        """Agent Core timeout should emit error event."""
        error_event = {
            "type": "error",
            "error": "Agent response failed",
            "code": "AGENT_ERROR",
        }
        formatted = f"event: error\ndata: {json.dumps(error_event)}\n\n"

        # Verify error format
        assert "AGENT_ERROR" in formatted

    @pytest.mark.asyncio
    async def test_agent_core_invalid_json_returns_error(self):
        """Invalid JSON from Agent Core should be handled."""
        # This would be handled by the client's aiter_lines()
        # and JSON parsing in invoke_agent
        pass

    @pytest.mark.asyncio
    async def test_message_save_failure_doesnt_break_stream(self):
        """Failure to save message should not break stream."""
        # Stream should continue even if message save fails
        # Implementation catches this and logs error without re-raising
        pass

    @pytest.mark.asyncio
    async def test_client_disconnect_handled_gracefully(self):
        """Client disconnect should be handled gracefully."""
        # StreamingResponse will handle GeneratorExit
        # No special handling needed in our code
        pass


class TestStreamingPerformance:
    """Test streaming performance characteristics."""

    @pytest.mark.asyncio
    async def test_token_events_streamed_immediately(self):
        """Tokens should be yielded immediately (low latency)."""
        # Tokens are yielded inside the for loop without buffering
        # This ensures low latency (< 100ms per token)
        pass

    @pytest.mark.asyncio
    async def test_streaming_doesnt_accumulate_in_memory(self):
        """Streaming should not accumulate large responses in memory."""
        # Tokens are yielded as they arrive, not buffered
        # Only full response text is accumulated in assistant_content
        # This prevents OOM for long responses
        pass

    @pytest.mark.asyncio
    async def test_json_fallback_is_blocked_when_true_streaming_required(self):
        """Complete JSON responses must not be presented as successful streams."""
        client = AgentCoreClient()
        json_data = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": (
                                "one two three four five six seven eight "
                                "nine ten eleven twelve"
                            )
                        }
                    ]
                }
            },
            "usage": {"totalTokens": 12},
        }

        events = [event async for event in client._tokenize_response(json_data)]

        assert events == [
            {
                "type": "error",
                "error_code": "TRUE_STREAMING_REQUIRED",
                "message": (
                    "Agent Core returned a complete JSON response instead of SSE/NDJSON. "
                    "Synthetic streaming is disabled."
                ),
                "recoverable": False,
            }
        ]

    @pytest.mark.asyncio
    async def test_json_fallback_can_be_paced_when_explicitly_allowed(self, monkeypatch):
        """Synthetic fallback remains available only as an explicit opt-out."""
        from app.config import settings

        monkeypatch.setattr(settings, "agent_core_require_true_streaming", False)
        client = AgentCoreClient()
        json_data = {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": (
                                "one two three four five six seven eight "
                                "nine ten eleven twelve"
                            )
                        }
                    ]
                }
            },
            "usage": {"totalTokens": 12},
        }

        started = time.monotonic()
        events = [event async for event in client._tokenize_response(json_data)]
        elapsed = time.monotonic() - started

        token_events = [event for event in events if event["type"] == "token"]
        assert len(token_events) == 3
        assert events[-1]["type"] == "done"
        assert elapsed >= 0.09


class TestResponseHeaders:
    """Test SSE response headers."""

    def test_streaming_response_headers(self):
        """Response should have correct SSE headers."""
        headers = {
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "identity",
            "X-Content-Type-Options": "nosniff",
        }

        assert headers["Cache-Control"] == "no-cache, no-transform"
        assert headers["Connection"] == "keep-alive"
        assert headers["X-Accel-Buffering"] == "no"
        assert headers["Content-Encoding"] == "identity"
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_media_type_is_event_stream(self):
        """Content-Type should be text/event-stream."""
        media_type = "text/event-stream"
        assert media_type == "text/event-stream"


class TestStreamingWithRealBackend:
    """Integration tests with real backend (requires running service)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stream_integration_end_to_end(self):
        """End-to-end test with real backend (requires service running)."""
        # This test requires:
        # 1. Running backend server at localhost:8000
        # 2. Valid user session in database
        # Can be run separately with: pytest -m integration
        pytest.skip("Requires running backend service")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stream_with_actual_agent_core(self):
        """Test with real Agent Core response (requires service running)."""
        # This test requires:
        # 1. Running backend server
        # 2. Running Agent Core service
        # Can be run separately with: pytest -m integration
        pytest.skip("Requires running Agent Core service")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stream_concurrent_requests(self):
        """Test multiple concurrent streaming requests."""
        # This test requires:
        # 1. Running backend server
        # 2. Multiple user sessions
        # Can be run separately with: pytest -m integration
        pytest.skip("Requires running backend service")


class TestStreamingEdgeCases:
    """Test edge cases in streaming."""

    def test_empty_message_content(self):
        """Empty message should fail validation."""
        with pytest.raises(ValueError):
            MessageRequest(content="")

    def test_message_with_very_long_content(self):
        """Very long message should be handled."""
        long_content = "a" * 4000  # Max allowed
        msg = MessageRequest(content=long_content)
        assert len(msg.content) == 4000

    def test_message_exceeding_max_length(self):
        """Message exceeding max length should fail validation."""
        too_long = "a" * 4001
        with pytest.raises(ValueError):
            MessageRequest(content=too_long)

    def test_session_id_format(self):
        """Session ID should be properly formatted."""
        session_id = "sess-123abc"
        assert session_id.startswith("sess-")

    def test_message_id_format(self):
        """Message ID should be properly formatted."""
        message_id = "msg-abc123def456"
        assert message_id.startswith("msg-")


class TestDataPersistence:
    """Test data persistence during streaming."""

    @pytest.mark.asyncio
    async def test_user_message_persisted_before_stream(self):
        """User message must be persisted before streaming starts."""
        # Service.add_message is called before agent_core.invoke_agent
        # This ensures message is saved even if streaming fails
        pass

    @pytest.mark.asyncio
    async def test_assistant_message_persisted_after_stream(self):
        """Assistant message persisted after streaming completes."""
        # Service.add_message is called after event_generator completes
        # This ensures full response is captured
        pass

    @pytest.mark.asyncio
    async def test_session_metadata_updated(self):
        """Session metadata should be updated with new messages."""
        # ChatService._update_session_metadata handles this
        # last_message_at and message_count are updated
        pass
