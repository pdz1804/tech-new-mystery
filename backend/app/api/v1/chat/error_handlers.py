"""Error handling and recovery for chatbot endpoints.

This module provides comprehensive error handling and recovery strategies for:
- Agent Core timeout
- Tool execution failures
- Session not found
- DynamoDB failures
- Invalid input
- Message persistence failures

Recovery strategies:
- Exponential backoff for transient failures
- Fallback responses
- Message queueing for failed saves
- Graceful degradation for non-critical features
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any, Callable, AsyncGenerator
from enum import Enum

from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error types for chatbot operations."""
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    TOOL_EXECUTION_FAILURE = "TOOL_EXECUTION_FAILURE"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MESSAGE_SAVE_FAILURE = "MESSAGE_SAVE_FAILURE"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class RecoveryStrategy(Enum):
    """Recovery strategies for different failure scenarios."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FALLBACK_RESPONSE = "fallback_response"
    MESSAGE_QUEUE = "message_queue"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    RETRY = "retry"


class ChatbotException(Exception):
    """Base exception for chatbot operations."""
    def __init__(
        self,
        error_type: ErrorType,
        user_message: str,
        status_code: int,
        technical_details: Optional[str] = None,
        recovery_strategy: Optional[RecoveryStrategy] = None,
    ):
        self.error_type = error_type
        self.user_message = user_message
        self.status_code = status_code
        self.technical_details = technical_details
        self.recovery_strategy = recovery_strategy
        super().__init__(user_message)


class AgentTimeoutError(ChatbotException):
    """Agent Core timed out waiting for response."""
    def __init__(self, timeout_seconds: int = 60):
        super().__init__(
            error_type=ErrorType.AGENT_TIMEOUT,
            user_message="Agent is taking longer than expected, please try again",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            technical_details=f"Agent did not respond within {timeout_seconds}s",
            recovery_strategy=RecoveryStrategy.RETRY,
        )


class ToolExecutionError(ChatbotException):
    """Tool execution failed but should not fail the request."""
    def __init__(self, tool_name: str, error_details: str):
        super().__init__(
            error_type=ErrorType.TOOL_EXECUTION_FAILURE,
            user_message=f"Tool '{tool_name}' encountered an issue, continuing without it",
            status_code=status.HTTP_200_OK,  # Continue streaming
            technical_details=f"Tool {tool_name} failed: {error_details}",
            recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
        )


class SessionNotFoundError(ChatbotException):
    """Session does not exist or was deleted."""
    def __init__(self, session_id: str):
        super().__init__(
            error_type=ErrorType.SESSION_NOT_FOUND,
            user_message="Session not found. Create a new session to continue.",
            status_code=status.HTTP_404_NOT_FOUND,
            technical_details=f"Session {session_id} not found in database",
            recovery_strategy=None,
        )


class DatabaseError(ChatbotException):
    """DynamoDB operation failed."""
    def __init__(self, operation: str, error_details: str):
        super().__init__(
            error_type=ErrorType.DATABASE_ERROR,
            user_message="Unable to save message, but agent response received",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            technical_details=f"DynamoDB {operation} failed: {error_details}",
            recovery_strategy=RecoveryStrategy.MESSAGE_QUEUE,
        )


class InvalidInputError(ChatbotException):
    """Invalid request input."""
    def __init__(self, validation_error: str):
        super().__init__(
            error_type=ErrorType.INVALID_INPUT,
            user_message="Invalid message format. Please check your input.",
            status_code=status.HTTP_400_BAD_REQUEST,
            technical_details=f"Input validation failed: {validation_error}",
            recovery_strategy=None,
        )


class AgentUnavailableError(ChatbotException):
    """Agent Core service is unavailable."""
    def __init__(self):
        super().__init__(
            error_type=ErrorType.AGENT_UNAVAILABLE,
            user_message="The AI service is temporarily unavailable, please try again later",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            technical_details="Agent Core Runtime service is not responding",
            recovery_strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
        )


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 5.0,
        exponential_base: float = 2.0,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class ErrorHandler:
    """Handles errors and applies recovery strategies."""

    def __init__(self):
        self.message_queue: list[Dict[str, Any]] = []
        self.retry_config = RetryConfig()

    async def handle_agent_timeout(
        self,
        session_id: str,
        user_message: str,
    ) -> None:
        """Handle Agent Core timeout."""
        logger.error(
            f"[TIMEOUT] Agent did not respond for session {session_id}",
            extra={"session_id": session_id, "user_message": user_message}
        )
        raise AgentTimeoutError()

    async def handle_tool_failure(
        self,
        tool_name: str,
        error: Exception,
    ) -> Dict[str, Any]:
        """Handle tool execution failure gracefully.

        Returns error event but doesn't fail the stream.
        """
        logger.warning(
            f"[TOOL_ERROR] Tool {tool_name} failed: {str(error)}",
            extra={"tool_name": tool_name, "error": str(error)},
            exc_info=True
        )
        return {
            "type": "error",
            "error_code": "TOOL_EXECUTION_FAILURE",
            "tool_name": tool_name,
            "message": f"Tool {tool_name} encountered an issue, continuing without it",
            "recoverable": True,
        }

    async def handle_session_not_found(self, session_id: str) -> None:
        """Handle session not found error."""
        logger.error(f"[SESSION_NOT_FOUND] Session {session_id} not found")
        raise SessionNotFoundError(session_id)

    async def handle_database_error(
        self,
        operation: str,
        error: Exception,
        should_queue: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Handle DynamoDB failures with queueing strategy.

        Args:
            operation: Operation that failed (e.g., 'save_message')
            error: Exception that occurred
            should_queue: Whether to queue failed operation for retry

        Returns:
            Error event dict if recoverable, raises otherwise
        """
        logger.error(
            f"[DATABASE_ERROR] {operation} failed: {str(error)}",
            extra={"operation": operation, "error": str(error)},
            exc_info=True
        )

        # Queue message if save failed (recoverable)
        if should_queue:
            return {
                "type": "error",
                "error_code": "MESSAGE_SAVE_DEFERRED",
                "message": "Unable to save message, but agent response received",
                "recoverable": True,
            }

        # Non-recoverable database error
        raise DatabaseError(operation, str(error))

    async def handle_invalid_input(self, validation_error: str) -> None:
        """Handle invalid request input."""
        logger.warning(f"[INVALID_INPUT] {validation_error}")
        raise InvalidInputError(validation_error)

    async def retry_with_backoff(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ):
        """Retry operation with exponential backoff.

        Args:
            operation: Async function to retry
            operation_name: Name for logging
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result of successful operation

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                logger.debug(f"[RETRY] {operation_name} - attempt {attempt + 1}")
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.warning(
                        f"[RETRY] {operation_name} failed, retrying in {delay}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[RETRY] {operation_name} failed after {self.retry_config.max_retries} retries"
                    )

        raise last_exception

    def queue_message_for_retry(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> str:
        """Queue message for later persistence.

        Args:
            session_id: Session ID
            user_id: User ID
            role: Message role
            content: Message content

        Returns:
            Queue ID for tracking
        """
        queue_id = f"queued-{uuid.uuid4().hex[:12]}"

        self.message_queue.append({
            "queue_id": queue_id,
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "created_at": asyncio.get_event_loop().time(),
        })

        logger.info(
            f"[MESSAGE_QUEUE] Queued message {queue_id} for session {session_id}"
        )
        return queue_id

    async def process_queued_messages(
        self,
        save_operation: Callable,
    ) -> Dict[str, Any]:
        """Process queued messages and attempt to save them.

        Args:
            save_operation: Async function to save a message

        Returns:
            Summary of processed messages
        """
        if not self.message_queue:
            return {"processed": 0, "failed": 0, "failed_ids": []}

        processed = 0
        failed = 0
        failed_ids = []

        for msg in self.message_queue[:]:  # Copy list to avoid modification during iteration
            try:
                await save_operation(
                    session_id=msg["session_id"],
                    user_id=msg["user_id"],
                    role=msg["role"],
                    content=msg["content"],
                )
                self.message_queue.remove(msg)
                processed += 1
                logger.info(f"[MESSAGE_QUEUE] Successfully saved {msg['queue_id']}")
            except Exception as e:
                failed += 1
                failed_ids.append(msg["queue_id"])
                logger.error(
                    f"[MESSAGE_QUEUE] Failed to save {msg['queue_id']}: {str(e)}"
                )

        return {
            "processed": processed,
            "failed": failed,
            "failed_ids": failed_ids,
            "remaining_in_queue": len(self.message_queue),
        }


class StreamingErrorHandler:
    """Handles errors during streaming responses."""

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler

    async def wrap_streaming_generator(
        self,
        generator: AsyncGenerator,
        session_id: str,
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """Wrap a streaming generator with error handling.

        Args:
            generator: Original async generator
            session_id: Session ID for context
            user_id: User ID for context

        Yields:
            SSE formatted events
        """
        try:
            async for event in generator:
                yield event
        except AgentTimeoutError as e:
            logger.error(f"[STREAM_ERROR] Agent timeout for session {session_id}")
            yield self._format_error_event(e)
        except ToolExecutionError as e:
            logger.warning(
                f"[STREAM_ERROR] Tool error for session {session_id}: {e.user_message}"
            )
            # Tool errors are non-fatal, continue streaming
            yield self._format_error_event(e)
        except DatabaseError as e:
            logger.error(f"[STREAM_ERROR] Database error for session {session_id}")
            # Queue the message and continue
            yield self._format_error_event(e)
        except ChatbotException as e:
            logger.error(f"[STREAM_ERROR] Chatbot error: {e.user_message}")
            yield self._format_error_event(e)
        except asyncio.TimeoutError:
            logger.error(f"[STREAM_ERROR] Operation timeout for session {session_id}")
            yield self._format_error_event_generic(
                "Operation timed out",
                ErrorType.AGENT_TIMEOUT,
            )
        except Exception as e:
            logger.error(
                f"[STREAM_ERROR] Unexpected error for session {session_id}: {str(e)}",
                exc_info=True
            )
            yield self._format_error_event_generic(
                "An unexpected error occurred",
                ErrorType.UNKNOWN_ERROR,
            )

    @staticmethod
    def _format_error_event(exc: ChatbotException) -> str:
        """Format error as SSE event."""
        event_data = {
            "type": "error",
            "error_code": exc.error_type.value,
            "message": exc.user_message,
            "recoverable": exc.recovery_strategy is not None,
        }
        return f"event: error\ndata: {json.dumps(event_data)}\n\n"

    @staticmethod
    def _format_error_event_generic(message: str, error_type: ErrorType) -> str:
        """Format generic error as SSE event."""
        event_data = {
            "type": "error",
            "error_code": error_type.value,
            "message": message,
            "recoverable": False,
        }
        return f"event: error\ndata: {json.dumps(event_data)}\n\n"


class InputValidator:
    """Validates chat request inputs."""

    @staticmethod
    def validate_message_request(content: str, max_length: int = 4000) -> None:
        """Validate message request content.

        Args:
            content: Message content
            max_length: Maximum content length

        Raises:
            InvalidInputError if validation fails
        """
        if not content:
            raise InvalidInputError("Message content cannot be empty")

        if len(content) > max_length:
            raise InvalidInputError(f"Message content exceeds {max_length} characters")

        if isinstance(content, str) and content.isspace():
            raise InvalidInputError("Message content cannot be whitespace only")

    @staticmethod
    def validate_session_id(session_id: str) -> None:
        """Validate session ID format.

        Args:
            session_id: Session ID to validate

        Raises:
            InvalidInputError if validation fails
        """
        if not session_id:
            raise InvalidInputError("Session ID is required")

        if len(session_id) > 255:
            raise InvalidInputError("Session ID too long")

    @staticmethod
    def validate_pagination(page: int, page_size: int, max_page_size: int = 100) -> None:
        """Validate pagination parameters.

        Args:
            page: Page number
            page_size: Page size
            max_page_size: Maximum allowed page size

        Raises:
            InvalidInputError if validation fails
        """
        if page < 1:
            raise InvalidInputError("Page must be >= 1")

        if page_size < 1 or page_size > max_page_size:
            raise InvalidInputError(f"Page size must be between 1 and {max_page_size}")
