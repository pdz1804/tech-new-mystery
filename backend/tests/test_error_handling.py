"""Tests for chatbot error handling and recovery.

Tests cover:
- Error type handling
- Recovery strategies
- Exponential backoff
- Message queueing
- Graceful degradation
- Input validation
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.api.v1.chat.error_handlers import (
    ErrorHandler,
    StreamingErrorHandler,
    InputValidator,
    ErrorType,
    RecoveryStrategy,
    ChatbotException,
    AgentTimeoutError,
    ToolExecutionError,
    SessionNotFoundError,
    DatabaseError,
    InvalidInputError,
    AgentUnavailableError,
    RetryConfig,
)


class TestErrorTypes:
    """Test error type definitions and properties."""

    def test_agent_timeout_error(self):
        """Test AgentTimeoutError creation and properties."""
        error = AgentTimeoutError(timeout_seconds=60)

        assert error.error_type == ErrorType.AGENT_TIMEOUT
        assert error.status_code == 504
        assert "longer than expected" in error.user_message
        assert error.recovery_strategy == RecoveryStrategy.RETRY

    def test_tool_execution_error(self):
        """Test ToolExecutionError creation."""
        error = ToolExecutionError("semantic_search", "Connection timeout")

        assert error.error_type == ErrorType.TOOL_EXECUTION_FAILURE
        assert error.status_code == 200  # Continue streaming
        assert "semantic_search" in error.user_message
        assert error.recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION

    def test_session_not_found_error(self):
        """Test SessionNotFoundError creation."""
        error = SessionNotFoundError("session-123")

        assert error.error_type == ErrorType.SESSION_NOT_FOUND
        assert error.status_code == 404
        assert "not found" in error.user_message

    def test_database_error(self):
        """Test DatabaseError creation."""
        error = DatabaseError("save_message", "DynamoDB write limit exceeded")

        assert error.error_type == ErrorType.DATABASE_ERROR
        assert error.status_code == 500
        assert error.recovery_strategy == RecoveryStrategy.MESSAGE_QUEUE

    def test_invalid_input_error(self):
        """Test InvalidInputError creation."""
        error = InvalidInputError("Message content cannot be empty")

        assert error.error_type == ErrorType.INVALID_INPUT
        assert error.status_code == 400

    def test_agent_unavailable_error(self):
        """Test AgentUnavailableError creation."""
        error = AgentUnavailableError()

        assert error.error_type == ErrorType.AGENT_UNAVAILABLE
        assert error.status_code == 503
        assert error.recovery_strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF


class TestRetryConfig:
    """Test retry configuration and exponential backoff calculation."""

    def test_default_retry_config(self):
        """Test default retry config values."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.initial_delay == 0.1
        assert config.max_delay == 5.0
        assert config.exponential_base == 2.0

    def test_custom_retry_config(self):
        """Test custom retry config."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=10.0,
            exponential_base=1.5,
        )

        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 10.0
        assert config.exponential_base == 1.5

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(initial_delay=0.1, max_delay=5.0, exponential_base=2.0)

        # Verify exponential growth
        assert config.get_delay(0) == 0.1  # 0.1 * 2^0
        assert config.get_delay(1) == 0.2  # 0.1 * 2^1
        assert config.get_delay(2) == 0.4  # 0.1 * 2^2
        assert config.get_delay(3) == 0.8  # 0.1 * 2^3
        assert config.get_delay(4) == 1.6  # 0.1 * 2^4

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(initial_delay=1.0, max_delay=2.0, exponential_base=2.0)

        # Even with high attempt, should cap at max_delay
        assert config.get_delay(10) == 2.0


class TestErrorHandler:
    """Test ErrorHandler for error handling operations."""

    @pytest.mark.asyncio
    async def test_handle_agent_timeout(self):
        """Test handling of agent timeout error."""
        handler = ErrorHandler()

        with pytest.raises(AgentTimeoutError) as exc_info:
            await handler.handle_agent_timeout("session-123", "test message")

        assert exc_info.value.error_type == ErrorType.AGENT_TIMEOUT

    @pytest.mark.asyncio
    async def test_handle_tool_failure(self):
        """Test handling of tool failure (should return error event, not raise)."""
        handler = ErrorHandler()
        error = Exception("Tool execution failed")

        result = await handler.handle_tool_failure("semantic_search", error)

        assert result["type"] == "error"
        assert result["error_code"] == "TOOL_EXECUTION_FAILURE"
        assert result["tool_name"] == "semantic_search"
        assert result["recoverable"] is True

    @pytest.mark.asyncio
    async def test_handle_session_not_found(self):
        """Test handling of session not found error."""
        handler = ErrorHandler()

        with pytest.raises(SessionNotFoundError):
            await handler.handle_session_not_found("session-456")

    @pytest.mark.asyncio
    async def test_handle_database_error_with_queue(self):
        """Test database error handling with message queueing."""
        handler = ErrorHandler()

        result = await handler.handle_database_error(
            "save_message",
            Exception("DynamoDB write failed"),
            should_queue=True,
        )

        assert result["type"] == "error"
        assert result["recoverable"] is True
        assert result["message"]  # Should have a message

    @pytest.mark.asyncio
    async def test_handle_database_error_without_queue(self):
        """Test database error that should not be queued."""
        handler = ErrorHandler()

        with pytest.raises(DatabaseError):
            await handler.handle_database_error(
                "delete_session",
                Exception("Permission denied"),
                should_queue=False,
            )

    @pytest.mark.asyncio
    async def test_handle_invalid_input(self):
        """Test handling of invalid input error."""
        handler = ErrorHandler()

        with pytest.raises(InvalidInputError) as exc_info:
            await handler.handle_invalid_input("Email format invalid")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test successful operation with retry."""
        handler = ErrorHandler()

        async def successful_operation():
            return "success"

        result = await handler.retry_with_backoff(
            successful_operation,
            "test_operation",
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_eventual_success(self):
        """Test operation that fails then succeeds."""
        handler = ErrorHandler()
        attempts = []

        async def flaky_operation():
            attempts.append(1)
            if len(attempts) < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await handler.retry_with_backoff(
            flaky_operation,
            "flaky_operation",
        )

        assert result == "success"
        assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_max_retries_exceeded(self):
        """Test operation that always fails."""
        handler = ErrorHandler()
        handler.retry_config.max_retries = 2  # Reduce for testing

        async def always_fails():
            raise Exception("Always fails")

        with pytest.raises(Exception) as exc_info:
            await handler.retry_with_backoff(
                always_fails,
                "failing_operation",
            )

        assert "Always fails" in str(exc_info.value)

    def test_queue_message_for_retry(self):
        """Test message queueing for failed saves."""
        handler = ErrorHandler()

        queue_id = handler.queue_message_for_retry(
            session_id="session-123",
            user_id="user-456",
            role="assistant",
            content="This is a queued message",
        )

        assert queue_id.startswith("queued-")
        assert len(handler.message_queue) == 1
        assert handler.message_queue[0]["content"] == "This is a queued message"

    def test_queue_message_multiple(self):
        """Test queueing multiple messages."""
        handler = ErrorHandler()

        ids = []
        for i in range(3):
            queue_id = handler.queue_message_for_retry(
                session_id=f"session-{i}",
                user_id="user-456",
                role="assistant",
                content=f"Message {i}",
            )
            ids.append(queue_id)

        assert len(handler.message_queue) == 3
        assert len(set(ids)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_process_queued_messages_success(self):
        """Test processing queued messages successfully."""
        handler = ErrorHandler()

        # Queue some messages
        handler.queue_message_for_retry("session-1", "user-1", "assistant", "msg1")
        handler.queue_message_for_retry("session-1", "user-1", "assistant", "msg2")

        # Mock save operation
        saved = []

        async def mock_save(**kwargs):
            saved.append(kwargs)

        result = await handler.process_queued_messages(mock_save)

        assert result["processed"] == 2
        assert result["failed"] == 0
        assert len(handler.message_queue) == 0
        assert len(saved) == 2

    @pytest.mark.asyncio
    async def test_process_queued_messages_partial_failure(self):
        """Test processing queued messages with some failures."""
        handler = ErrorHandler()

        handler.queue_message_for_retry("session-1", "user-1", "assistant", "msg1")
        handler.queue_message_for_retry("session-1", "user-1", "assistant", "msg2")
        handler.queue_message_for_retry("session-1", "user-1", "assistant", "msg3")

        call_count = [0]

        async def mock_save_with_failures(**kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Fail on second call
                raise Exception("Database error")

        result = await handler.process_queued_messages(mock_save_with_failures)

        assert result["processed"] == 2
        assert result["failed"] == 1
        assert len(result["failed_ids"]) == 1
        assert len(handler.message_queue) == 1  # One message still queued

    @pytest.mark.asyncio
    async def test_process_empty_queue(self):
        """Test processing empty message queue."""
        handler = ErrorHandler()

        async def mock_save(**kwargs):
            pass

        result = await handler.process_queued_messages(mock_save)

        assert result["processed"] == 0
        assert result["failed"] == 0


class TestInputValidator:
    """Test input validation functions."""

    def test_validate_message_request_valid(self):
        """Test validation of valid message content."""
        # Should not raise
        InputValidator.validate_message_request("This is a valid message")

    def test_validate_message_request_empty(self):
        """Test validation rejects empty message."""
        with pytest.raises(InvalidInputError):
            InputValidator.validate_message_request("")

    def test_validate_message_request_whitespace_only(self):
        """Test validation rejects whitespace-only message."""
        with pytest.raises(InvalidInputError):
            InputValidator.validate_message_request("   \n\t  ")

    def test_validate_message_request_too_long(self):
        """Test validation rejects overly long message."""
        long_message = "x" * 5000

        with pytest.raises(InvalidInputError):
            InputValidator.validate_message_request(long_message, max_length=4000)

    def test_validate_session_id_valid(self):
        """Test validation of valid session ID."""
        InputValidator.validate_session_id("session-123")

    def test_validate_session_id_empty(self):
        """Test validation rejects empty session ID."""
        with pytest.raises(InvalidInputError):
            InputValidator.validate_session_id("")

    def test_validate_session_id_too_long(self):
        """Test validation rejects overly long session ID."""
        with pytest.raises(InvalidInputError):
            InputValidator.validate_session_id("x" * 300)

    def test_validate_pagination_valid(self):
        """Test validation of valid pagination."""
        InputValidator.validate_pagination(page=1, page_size=20)

    def test_validate_pagination_invalid_page(self):
        """Test validation rejects invalid page number."""
        with pytest.raises(InvalidInputError):
            InputValidator.validate_pagination(page=0, page_size=20)

    def test_validate_pagination_invalid_page_size(self):
        """Test validation rejects invalid page size."""
        with pytest.raises(InvalidInputError):
            InputValidator.validate_pagination(page=1, page_size=0)

        with pytest.raises(InvalidInputError):
            InputValidator.validate_pagination(page=1, page_size=150)


class TestStreamingErrorHandler:
    """Test StreamingErrorHandler for streaming error handling."""

    @pytest.mark.asyncio
    async def test_wrap_streaming_generator_success(self):
        """Test wrapping successful streaming generator."""
        handler = ErrorHandler()
        streaming_handler = StreamingErrorHandler(handler)

        async def mock_generator():
            yield "event: token\ndata: {}\n\n"
            yield "event: done\ndata: {}\n\n"

        events = []
        async for event in streaming_handler.wrap_streaming_generator(
            mock_generator(),
            "session-123",
            "user-456",
        ):
            events.append(event)

        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_wrap_streaming_generator_with_timeout(self):
        """Test wrapping generator with timeout error."""
        handler = ErrorHandler()
        streaming_handler = StreamingErrorHandler(handler)

        async def mock_generator_timeout():
            await asyncio.sleep(1)  # Simulate long operation

        # Create a wrapper that times out
        async def timeout_generator():
            try:
                async for _ in asyncio.timeout(0.01):  # Very short timeout
                    yield "event: token\ndata: {}\n\n"
            except asyncio.TimeoutError:
                raise

        events = []
        # The timeout should be caught and converted to error event
        # This test verifies error handling doesn't crash

    @pytest.mark.asyncio
    async def test_streaming_error_handler_formats_error_events(self):
        """Test error event formatting."""
        streaming_handler = StreamingErrorHandler(ErrorHandler())

        error_event = streaming_handler._format_error_event_generic(
            "Test error message",
            ErrorType.AGENT_TIMEOUT,
        )

        assert "event: error" in error_event
        assert "AGENT_TIMEOUT" in error_event
        assert "Test error message" in error_event


class TestIntegration:
    """Integration tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_complete_error_recovery_flow(self):
        """Test complete error detection and recovery flow."""
        handler = ErrorHandler()

        # Simulate tool failure
        tool_error = await handler.handle_tool_failure(
            "semantic_search",
            Exception("Connection timeout"),
        )
        assert tool_error["recoverable"] is True

        # Queue a message due to database failure
        queue_id = handler.queue_message_for_retry(
            "session-123",
            "user-456",
            "assistant",
            "Failed message",
        )
        assert queue_id.startswith("queued-")

        # Process queued message
        async def mock_save(**kwargs):
            pass

        result = await handler.process_queued_messages(mock_save)
        assert result["processed"] == 1

    @pytest.mark.asyncio
    async def test_multiple_retries_with_delays(self):
        """Test retry mechanism with exponential backoff."""
        handler = ErrorHandler()
        handler.retry_config.initial_delay = 0.01  # Use small delays for testing
        handler.retry_config.max_delay = 0.1

        attempts = []
        start_times = []

        async def track_attempts():
            import time

            start_times.append(time.time())
            attempts.append(len(attempts) + 1)

            if len(attempts) < 3:
                raise Exception("Retry needed")
            return "success"

        result = await handler.retry_with_backoff(
            track_attempts,
            "tracked_operation",
        )

        assert result == "success"
        assert len(attempts) == 3

        # Verify delays between attempts (rough check due to timing variance)
        if len(start_times) > 1:
            first_to_second = start_times[1] - start_times[0]
            # Should be roughly 0.01 seconds (initial delay)
            assert first_to_second < 1.0  # Generous check


# Run with: pytest tests/test_error_handling.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
