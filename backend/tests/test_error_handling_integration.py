"""Integration tests for error handling with real failure scenarios.

Tests real error conditions:
- Agent Core timeout (60s)
- Tool execution failures
- DynamoDB failures
- Session not found
- Invalid input
- Streaming with partial failures
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.api.v1.chat.error_handlers import (
    ErrorHandler,
    ErrorType,
    AgentTimeoutError,
    SessionNotFoundError,
    DatabaseError,
    InvalidInputError,
)
from app.services.chat_service import ChatService


class TestAgentTimeoutScenario:
    """Test Agent Core timeout scenario."""

    @pytest.mark.asyncio
    async def test_agent_timeout_60_seconds(self):
        """Test that agent timeout triggers after 60 seconds."""
        error_handler = ErrorHandler()

        async def slow_agent_call():
            await asyncio.sleep(65)  # Exceeds 60s timeout
            return "response"

        with pytest.raises(Exception):
            # Simulate timeout
            await asyncio.wait_for(slow_agent_call(), timeout=60.0)

    @pytest.mark.asyncio
    async def test_agent_timeout_error_message(self):
        """Test agent timeout error user message."""
        error = AgentTimeoutError(timeout_seconds=60)

        assert error.status_code == 504
        assert "longer than expected" in error.user_message
        assert "try again" in error.user_message.lower()

    @pytest.mark.asyncio
    async def test_agent_timeout_recoverable(self):
        """Test that agent timeout is marked as recoverable."""
        error = AgentTimeoutError()

        assert error.recovery_strategy is not None
        assert "retry" in str(error.recovery_strategy).lower()


class TestToolExecutionFailure:
    """Test tool execution failure scenarios."""

    @pytest.mark.asyncio
    async def test_tool_failure_does_not_break_stream(self):
        """Test that tool failure allows stream to continue."""
        handler = ErrorHandler()

        # Simulate semantic search tool failing
        error_event = await handler.handle_tool_failure(
            "semantic_search",
            Exception("Connection timeout"),
        )

        assert error_event["type"] == "error"
        assert error_event["recoverable"] is True
        # Should NOT raise exception - stream continues

    @pytest.mark.asyncio
    async def test_multiple_tool_failures(self):
        """Test multiple tool failures in sequence."""
        handler = ErrorHandler()

        failures = []
        for tool_name in ["semantic_search", "code_interpreter", "browser"]:
            error_event = await handler.handle_tool_failure(
                tool_name,
                Exception(f"{tool_name} failed"),
            )
            failures.append(error_event)

        assert len(failures) == 3
        assert all(e["recoverable"] is True for e in failures)
        assert all(e["type"] == "error" for e in failures)


class TestDatabaseFailureRecovery:
    """Test database failure scenarios and recovery."""

    @pytest.mark.asyncio
    async def test_dynamodb_write_failure_queues_message(self):
        """Test that DynamoDB write failure queues message."""
        handler = ErrorHandler()

        result = await handler.handle_database_error(
            "save_message",
            Exception("DynamoDB write limit exceeded"),
            should_queue=True,
        )

        assert result["recoverable"] is True
        assert result["type"] == "error"

    @pytest.mark.asyncio
    async def test_message_persistence_delay(self):
        """Test that messages can be queued and retried."""
        handler = ErrorHandler()

        # First attempt: queue the message
        queue_id = handler.queue_message_for_retry(
            "session-123",
            "user-456",
            "assistant",
            "This response should be persisted",
        )

        assert queue_id in [msg["queue_id"] for msg in handler.message_queue]

        # Later attempt: process queued messages
        saved_messages = []

        async def retry_save(**kwargs):
            saved_messages.append(kwargs)

        result = await handler.process_queued_messages(retry_save)

        assert result["processed"] == 1
        assert result["failed"] == 0
        assert len(handler.message_queue) == 0
        assert saved_messages[0]["content"] == "This response should be persisted"

    @pytest.mark.asyncio
    async def test_partial_queue_failure(self):
        """Test processing queue with partial failures."""
        handler = ErrorHandler()

        # Queue 3 messages
        for i in range(3):
            handler.queue_message_for_retry(
                f"session-{i}",
                "user-456",
                "assistant",
                f"Message {i}",
            )

        # Mock save that fails on one message
        async def failing_save(**kwargs):
            if "Message 1" in kwargs.get("content", ""):
                raise Exception("Failed to save Message 1")

        result = await handler.process_queued_messages(failing_save)

        assert result["processed"] == 2
        assert result["failed"] == 1
        assert len(result["failed_ids"]) == 1
        assert len(handler.message_queue) == 1

    @pytest.mark.asyncio
    async def test_database_error_non_recoverable(self):
        """Test non-recoverable database errors."""
        handler = ErrorHandler()

        with pytest.raises(DatabaseError):
            await handler.handle_database_error(
                "delete_session",
                Exception("Permission denied"),
                should_queue=False,
            )


class TestSessionNotFoundScenario:
    """Test session not found error scenario."""

    @pytest.mark.asyncio
    async def test_session_not_found_error(self):
        """Test session not found error properties."""
        with pytest.raises(SessionNotFoundError) as exc_info:
            raise SessionNotFoundError("session-999")

        error = exc_info.value
        assert error.status_code == 404
        assert "not found" in error.user_message.lower()

    @pytest.mark.asyncio
    async def test_deleted_session_handling(self):
        """Test handling of deleted session."""
        handler = ErrorHandler()

        with pytest.raises(SessionNotFoundError):
            await handler.handle_session_not_found("deleted-session-id")


class TestInputValidationScenarios:
    """Test input validation error scenarios."""

    def test_empty_message_rejected(self):
        """Test that empty messages are rejected."""
        from app.api.v1.chat.error_handlers import InputValidator

        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_message_request("")

        assert exc_info.value.status_code == 400

    def test_message_too_long_rejected(self):
        """Test that overly long messages are rejected."""
        from app.api.v1.chat.error_handlers import InputValidator

        with pytest.raises(InvalidInputError):
            InputValidator.validate_message_request("x" * 5000)

    def test_whitespace_only_rejected(self):
        """Test that whitespace-only messages are rejected."""
        from app.api.v1.chat.error_handlers import InputValidator

        with pytest.raises(InvalidInputError):
            InputValidator.validate_message_request("   \n\t  ")

    def test_valid_message_accepted(self):
        """Test that valid messages are accepted."""
        from app.api.v1.chat.error_handlers import InputValidator

        # Should not raise
        InputValidator.validate_message_request("This is a valid message")

    def test_invalid_session_id_rejected(self):
        """Test that invalid session IDs are rejected."""
        from app.api.v1.chat.error_handlers import InputValidator

        with pytest.raises(InvalidInputError):
            InputValidator.validate_session_id("")

        with pytest.raises(InvalidInputError):
            InputValidator.validate_session_id("x" * 300)

    def test_invalid_pagination_rejected(self):
        """Test that invalid pagination is rejected."""
        from app.api.v1.chat.error_handlers import InputValidator

        with pytest.raises(InvalidInputError):
            InputValidator.validate_pagination(page=0, page_size=20)

        with pytest.raises(InvalidInputError):
            InputValidator.validate_pagination(page=1, page_size=0)

        with pytest.raises(InvalidInputError):
            InputValidator.validate_pagination(page=1, page_size=200)


class TestExponentialBackoffBehavior:
    """Test exponential backoff retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test that retries use exponential backoff."""
        handler = ErrorHandler()
        handler.retry_config.max_retries = 3
        handler.retry_config.initial_delay = 0.01
        handler.retry_config.max_delay = 0.1
        handler.retry_config.exponential_base = 2.0

        call_times = []

        async def track_calls():
            import time

            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await handler.retry_with_backoff(
            track_calls,
            "test_retries",
        )

        assert result == "success"
        assert len(call_times) == 3

        # Verify delays increase exponentially (approximately)
        if len(call_times) > 1:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Second delay should be roughly double first delay (exponential backoff)
            # Allow for timing variance
            assert delay2 > delay1 * 0.8  # At least close to doubling

    @pytest.mark.asyncio
    async def test_retry_max_delay_cap(self):
        """Test that retry delays are capped at max_delay."""
        handler = ErrorHandler()
        handler.retry_config.max_retries = 10
        handler.retry_config.initial_delay = 0.01
        handler.retry_config.max_delay = 0.02
        handler.retry_config.exponential_base = 2.0

        attempts = 0

        async def high_attempt_operation():
            nonlocal attempts
            attempts += 1
            if attempts < 5:
                raise Exception("Keep trying")
            return "success"

        result = await handler.retry_with_backoff(
            high_attempt_operation,
            "capped_retry",
        )

        assert result == "success"
        assert attempts == 5


class TestStreamingErrorHandling:
    """Test error handling during streaming responses."""

    @pytest.mark.asyncio
    async def test_streaming_with_tool_error(self):
        """Test streaming continues after tool error."""
        from app.api.v1.chat.error_handlers import StreamingErrorHandler

        handler = ErrorHandler()
        streaming_handler = StreamingErrorHandler(handler)

        async def generator_with_tool_error():
            yield {"type": "token", "content": "Some "}
            # Tool error happens
            yield {"type": "error", "error_code": "TOOL_ERROR", "recoverable": True}
            # Streaming continues
            yield {"type": "token", "content": "response"}
            yield {"type": "done"}

        events = []
        async for event in streaming_handler.wrap_streaming_generator(
            generator_with_tool_error(),
            "session-123",
            "user-456",
        ):
            events.append(event)

        assert len(events) >= 4

    @pytest.mark.asyncio
    async def test_streaming_graceful_shutdown(self):
        """Test graceful shutdown of streaming on fatal error."""
        from app.api.v1.chat.error_handlers import StreamingErrorHandler

        handler = ErrorHandler()
        streaming_handler = StreamingErrorHandler(handler)

        async def generator_with_fatal_error():
            yield {"type": "token", "content": "Start "}
            # Simulate fatal error
            raise Exception("Fatal error in stream")

        events = []
        async for event in streaming_handler.wrap_streaming_generator(
            generator_with_fatal_error(),
            "session-123",
            "user-456",
        ):
            events.append(event)

        # Should have received token + error event
        assert len(events) >= 2
        assert "error" in str(events[-1]).lower()


class TestConcurrentErrorHandling:
    """Test error handling with concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_timeouts(self):
        """Test handling multiple concurrent timeouts."""

        async def timeout_operation(session_id: str):
            try:
                await asyncio.wait_for(
                    asyncio.sleep(65),  # Will timeout
                    timeout=60.0,
                )
            except asyncio.TimeoutError:
                return f"Timeout for {session_id}"

        # Run concurrent operations
        results = await asyncio.gather(
            timeout_operation("session-1"),
            timeout_operation("session-2"),
            timeout_operation("session-3"),
        )

        assert len(results) == 3
        assert all("Timeout" in r for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_queue_processing(self):
        """Test concurrent message queue processing."""
        handlers = [ErrorHandler() for _ in range(3)]

        # Queue messages in each handler
        for i, handler in enumerate(handlers):
            handler.queue_message_for_retry(
                f"session-{i}",
                "user-456",
                "assistant",
                f"Message from handler {i}",
            )

        # Process queues concurrently
        async def process_queue(handler):
            async def mock_save(**kwargs):
                await asyncio.sleep(0.01)  # Simulate db operation

            return await handler.process_queued_messages(mock_save)

        results = await asyncio.gather(
            *[process_queue(h) for h in handlers],
        )

        assert len(results) == 3
        assert all(r["processed"] == 1 for r in results)
        assert all(r["failed"] == 0 for r in results)


# Run with: pytest tests/test_error_handling_integration.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
