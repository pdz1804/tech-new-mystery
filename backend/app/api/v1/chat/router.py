"""Chat endpoints."""

import asyncio
import inspect
import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Query, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_request_agent_memory
from app.api.v1.chat.auth import get_chat_auth_user, validate_session_ownership
from app.api.v1.chat.schemas import (
    CreateSessionRequest,
    SessionResponse,
    MessageRequest,
    MessageResponse,
    SessionListResponse,
    MessageListResponse,
    UpdateSessionRequest,
)
from app.api.v1.chat.error_handlers import (
    ErrorHandler,
    InputValidator,
    InvalidInputError,
)
from app.services.chat_service import ChatService
from app.integrations.agent_core_client import AgentCoreClient
from app.integrations.agent_core_memory import RequestAgentMemory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
SSE_FLUSH_PAUSE_SECONDS = 0.005


def _sse(event_type: str, data: dict) -> str:
    """Format a single Server-Sent Event."""
    payload = {
        **data,
        "_server_sent_at_ms": int(time.time() * 1000),
    }
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


async def _yield_sse(event_type: str, data: dict) -> AsyncGenerator[str, None]:
    """Yield one SSE frame and hand control back to the ASGI server.

    The explicit event-loop yield matters when an upstream stream delivers many
    small events in one burst. Without it, Uvicorn/Starlette can enqueue several
    frames before the socket gets a chance to flush to the browser.
    """
    yield _sse(event_type, data)
    await asyncio.sleep(SSE_FLUSH_PAUSE_SECONDS)


async def _iterate_with_timeout(
    stream: AsyncGenerator[dict, None],
    timeout: float,
) -> AsyncGenerator[dict, None]:
    """Apply an overall timeout to an async event stream."""
    if inspect.isawaitable(stream):
        stream = await stream

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError()

        try:
            event = await asyncio.wait_for(anext(stream), timeout=remaining)
        except StopAsyncIteration:
            return

        yield event


@router.post("/sessions", response_model=dict, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    current_user: dict = Depends(get_chat_auth_user),
) -> dict:
    """Create a new chat session with error handling.

    Args:
        payload: Session creation request
        current_user: Current authenticated user

    Returns:
        Created session object

    Raises:
        400: Invalid input
        500: Database error
    """
    error_handler = ErrorHandler()

    try:
        # Validate input
        if not payload.title or len(payload.title) == 0:
            raise InvalidInputError("Session title cannot be empty")

        if len(payload.title) > 255:
            raise InvalidInputError("Session title exceeds maximum length")

        service = ChatService()

        # Retry database operation with exponential backoff
        session = await error_handler.retry_with_backoff(
            service.create_session,
            "create_session",
            user_id=current_user["sub"],
            title=payload.title,
            description=payload.description,
        )
        return {"success": True, "data": session}

    except InvalidInputError as e:
        logger.warning(f"Invalid input for create_session: {e.user_message}")
        raise HTTPException(status_code=e.status_code, detail=e.user_message)

    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: dict = Depends(get_chat_auth_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SessionListResponse:
    """List user's chat sessions (sorted by recency) with error handling.

    Args:
        current_user: Current authenticated user
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        List of sessions with pagination metadata

    Raises:
        400: Invalid pagination parameters
        500: Database error
    """
    error_handler = ErrorHandler()

    try:
        # Validate pagination
        InputValidator.validate_pagination(page, page_size)

        service = ChatService()
        result = await error_handler.retry_with_backoff(
            service.list_sessions,
            "list_sessions",
            user_id=current_user["sub"],
            page=page,
            page_size=page_size,
        )
        return SessionListResponse(
            success=True,
            data=[SessionResponse(**s) for s in result["sessions"]],
            meta={
                "page": result["page"],
                "limit": result["page_size"],
                "total": result["total"],
                "last_key": None,
            },
        )

    except InvalidInputError as e:
        raise HTTPException(status_code=e.status_code, detail=e.user_message)

    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions",
        )


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_chat_auth_user),
    session: dict = Depends(validate_session_ownership),
) -> dict:
    """Get session details (session owner only) with error handling.

    Args:
        session_id: Session ID
        current_user: Current authenticated user (requires valid JWT token)
        session: Validated session (auth & ownership checked)

    Returns:
        Session object

    Raises:
        400: Invalid session ID
        401: No token or invalid token
        404: Session not found
        403: User doesn't own this session
    """
    try:
        # Validate session ID
        InputValidator.validate_session_id(session_id)

        logger.debug(
            f"[GET_SESSION] User {current_user['sub']} retrieved session {session_id}"
        )
        return {"success": True, "data": session}

    except InvalidInputError as e:
        raise HTTPException(status_code=e.status_code, detail=e.user_message)


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_messages(
    session_id: str,
    current_user: dict = Depends(get_chat_auth_user),
    session: dict = Depends(validate_session_ownership),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> MessageListResponse:
    """Get session message history with pagination (session owner only).

    Args:
        session_id: Session ID
        current_user: Current authenticated user
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        List of messages with pagination metadata

    Raises:
        400: Invalid pagination parameters
        404: Session not found
        403: User doesn't own this session
        500: Database error
    """
    error_handler = ErrorHandler()

    try:
        # Validate session ID and pagination
        InputValidator.validate_session_id(session_id)
        InputValidator.validate_pagination(page, page_size)

        service = ChatService()
        result = await error_handler.retry_with_backoff(
            service.get_messages,
            "get_messages",
            session_id=session_id,
            user_id=current_user["sub"],
            page=page,
            page_size=page_size,
        )
        return MessageListResponse(
            success=True,
            data=[MessageResponse(**m) for m in result["messages"]],
            meta={
                "page": result["page"],
                "limit": result["page_size"],
                "total": result["total"],
                "last_key": None,
            },
        )

    except InvalidInputError as e:
        raise HTTPException(status_code=e.status_code, detail=e.user_message)

    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this session",
        )

    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages",
        )


@router.post("/sessions/{session_id}/message", response_model=dict, status_code=201)
async def add_message(
    session_id: str,
    payload: MessageRequest,
    current_user: dict = Depends(get_chat_auth_user),
    session: dict = Depends(validate_session_ownership),
) -> dict:
    """Add a user message to a chat session with error handling.

    Args:
        session_id: Session ID
        payload: Message request with user content
        current_user: Current authenticated user

    Returns:
        Created message object

    Raises:
        400: Invalid message or session ID
        404: Session not found
        403: User doesn't own this session
        500: Database error
    """
    error_handler = ErrorHandler()

    try:
        # Validate inputs
        InputValidator.validate_session_id(session_id)
        InputValidator.validate_message_request(payload.content)

        service = ChatService()
        message = await error_handler.retry_with_backoff(
            service.add_message,
            "add_message",
            session_id=session_id,
            user_id=current_user["sub"],
            role="user",
            content=payload.content,
        )
        return {"success": True, "data": message}

    except InvalidInputError as e:
        raise HTTPException(status_code=e.status_code, detail=e.user_message)

    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this session",
        )

    except Exception as e:
        logger.error(f"Failed to add message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save message",
        )


@router.put("/sessions/{session_id}", response_model=dict)
async def rename_session(
    session_id: str,
    payload: UpdateSessionRequest,
    current_user: dict = Depends(get_chat_auth_user),
    session: dict = Depends(validate_session_ownership),
) -> dict:
    """Rename a session."""
    InputValidator.validate_session_id(session_id)
    service = ChatService()
    updated = await service.rename_session(session_id, current_user["sub"], payload.title)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"success": True, "data": updated}


@router.put("/sessions/{session_id}/archive", response_model=dict)
async def archive_session(
    session_id: str,
    current_user: dict = Depends(get_chat_auth_user),
    session: dict = Depends(validate_session_ownership),
) -> dict:
    """Archive a session."""
    InputValidator.validate_session_id(session_id)
    service = ChatService()
    ok = await service.archive_session(session_id, current_user["sub"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    archived = await service.get_session(session_id, current_user["sub"])
    if not archived:
        # session may no longer be active in listing path; fetch raw state via rename helper pattern
        archived = {"session_id": session_id, "user_id": current_user["sub"], "is_active": False}
    return {"success": True, "data": archived}


@router.put("/sessions/{session_id}/restore", response_model=dict)
async def restore_session(
    session_id: str,
    current_user: dict = Depends(get_chat_auth_user),
) -> dict:
    """Restore an archived session."""
    InputValidator.validate_session_id(session_id)
    service = ChatService()
    restored = await service.restore_session(session_id, current_user["sub"])
    if not restored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"success": True, "data": restored}


@router.delete("/sessions/{session_id}", response_model=dict)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_chat_auth_user),
) -> dict:
    """Delete a session and all associated messages."""
    InputValidator.validate_session_id(session_id)
    service = ChatService()
    ok = await service.delete_session(session_id, current_user["sub"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"success": True, "message": "Session deleted"}


@router.post("/sessions/{session_id}/stream")
async def stream_chat_message(
    session_id: str,
    payload: MessageRequest,
    request: Request,
    current_user: dict = Depends(get_chat_auth_user),
    session: dict = Depends(validate_session_ownership),
    req_memory: RequestAgentMemory = Depends(get_request_agent_memory),
) -> StreamingResponse:
    """Stream chat response as Server-Sent Events (SSE) with comprehensive error handling.

    CHT-018 Implementation: Comprehensive error handling and recovery

    Error handling for:
    - Agent Core timeout (60s): 504 with user-friendly message
    - Tool execution failure: Continue streaming with error event
    - Session not found: 404 with clear message
    - DynamoDB failures: Queue message, continue streaming
    - Invalid input: 400 with validation error
    - Memory initialization timeout: 503 with retry guidance

    Recovery strategies:
    - Exponential backoff for transient failures
    - Message queueing for failed saves
    - Graceful degradation (continue without failed tools)
    - Partial message save (save what we have)

    Streamed events:
    - token: Individual text chunks from agent response
    - tool_invocation: When agent calls a tool
    - tool_result: Results from tool execution
    - done: Final completion signal
    - error: Errors during streaming (recoverable or fatal)

    Args:
        session_id: Session ID to stream response to
        payload: Message request with user content
        current_user: Current authenticated user
        req_memory: Per-request isolated memory (injected by FastAPI)

    Returns:
        StreamingResponse with text/event-stream media type

    Raises:
        400: Invalid message or session ID
        404: Session not found
        403: User doesn't own this session
        503: Memory load timeout
        504: Agent Core timeout
    """
    error_handler = ErrorHandler()
    service = ChatService()
    user_id = current_user["sub"]

    # 1. VALIDATE: Session exists and user owns it
    try:
        InputValidator.validate_session_id(session_id)
        InputValidator.validate_message_request(payload.content)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        if session.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access this session",
            )
    except InvalidInputError as e:
        raise HTTPException(status_code=e.status_code, detail=e.user_message)
    except ValueError as e:
        logger.error(f"Session validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this session",
        )

    # 2. ISOLATION: Initialize per-request memory with timeout
    try:
        # Load recent messages from DynamoDB as context
        messages_result = await asyncio.wait_for(
            service.get_messages(session_id, user_id, page_size=10),
            timeout=15.0,  # Increased from 5.0 to allow DynamoDB queries
        )
        recent_events = [
            {
                "role": m["role"],
                "content": m["content"],
                "timestamp": m["timestamp"],
                "event_id": m["message_id"],
            }
            for m in messages_result["messages"]
        ]

        # Initialize per-request memory with context
        await asyncio.wait_for(
            req_memory.initialize(
                session_id=session_id,
                user_id=user_id,
                recent_events=recent_events,
            ),
            timeout=5.0,
        )
        logger.debug(
            f"[STREAM] Memory initialized for session {session_id}, user {user_id}"
        )
    except asyncio.TimeoutError:
        logger.error(f"[STREAM] Memory initialization timeout for session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory initialization timeout. Please try again.",
        )
    except Exception as e:
        logger.error(f"[STREAM] Memory initialization error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Memory initialization failed",
        )

    # 3. SAVE: User message immediately with retry
    try:
        await error_handler.retry_with_backoff(
            service.add_message,
            "save_user_message",
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=payload.content,
        )
        # Log to per-request memory
        await req_memory.log_message(
            session_id=session_id,
            role="user",
            content=payload.content,
        )
    except Exception as e:
        logger.error(f"[STREAM] Failed to save user message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save user message",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for streaming response with error handling.

        This generator maintains isolation within the request scope,
        applies recovery strategies for failures, and ensures cleanup.
        """
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        assistant_content = ""
        agent_core: AgentCoreClient | None = None
        agent_stream = None

        try:
            # Flush response headers immediately so proxies and browsers commit
            # to streaming before the first model/tool event is available.
            yield f": stream-open {' ' * 2048}\n\n"
            await asyncio.sleep(SSE_FLUSH_PAUSE_SECONDS)

            agent_core = AgentCoreClient()
            agent_stream = agent_core.invoke_agent(
                session_id=session_id,
                user_message=payload.content,
                context={
                    "recent_events": recent_events,
                    "request_scope": "isolated",
                },
                user_id=user_id,
            )

            # Stream response from Agent Core with error handling
            try:
                event_count = 0
                async for event in _iterate_with_timeout(
                    agent_stream,
                    timeout=300.0,
                ):
                    event_count += 1
                    event_type = event.get("type", "unknown")
                    logger.debug(f"[STREAM] Event #{event_count} received: type={event_type}, has_content={bool(event.get('content'))}")

                    # Handle token events (text chunks)
                    if event_type == "token":
                        token_content = event.get("content", "")
                        assistant_content += token_content
                        logger.debug(f"[STREAM] Yielding token event, content_len={len(token_content)}")
                        async for frame in _yield_sse("token", event):
                            yield frame
                        if await request.is_disconnected():
                            logger.info("[STREAM] Client disconnected, stopping stream")
                            return

                    # Handle tool invocation events
                    elif event_type == "tool_invocation":
                        async for frame in _yield_sse("tool_invocation", event):
                            yield frame
                        if await request.is_disconnected():
                            logger.info("[STREAM] Client disconnected, stopping stream")
                            return

                    # Handle tool result events
                    elif event_type == "tool_result":
                        async for frame in _yield_sse("tool_result", event):
                            yield frame
                        if await request.is_disconnected():
                            logger.info("[STREAM] Client disconnected, stopping stream")
                            return

                    # Handle error events from agent (recoverable)
                    elif event_type == "error":
                        logger.warning(f"Agent error (recoverable): {event.get('message')}")
                        async for frame in _yield_sse("error", event):
                            yield frame
                        # Continue streaming - don't return

                    elif event_type == "done":
                        logger.debug(f"Agent Core done event received for session {session_id}")
                        # Agent Core emits an internal done before the backend has
                        # persisted the assistant message. Suppress it so the
                        # browser receives one authoritative final done event
                        # with message_id/tokens after save.
                        continue

                    # Handle stream_diagnostic and other events
                    elif event_type == "stream_diagnostic":
                        logger.debug(f"Stream diagnostic: {event.get('phase')}")
                        # Don't yield diagnostic events to frontend

                    # Handle any other events
                    else:
                        content = event.get("content")
                        if isinstance(content, str):
                            assistant_content += content
                        async for frame in _yield_sse(event_type, event):
                            yield frame
                        if await request.is_disconnected():
                            logger.info("[STREAM] Client disconnected, stopping stream")
                            return

            except asyncio.TimeoutError:
                # Agent Core timeout: 300 seconds (5 minutes)
                logger.error(
                    f"[TIMEOUT] Agent Core timeout for session {session_id} after 300s"
                )
                error_event = {
                    "type": "error",
                    "error_code": "AGENT_TIMEOUT",
                    "message": "Agent is taking longer than expected, please try again",
                    "recoverable": True,
                }
                async for frame in _yield_sse("error", error_event):
                    yield frame
                return

            except Exception as agent_error:
                # Agent Core unavailable or other error
                logger.error(
                    f"[AGENT_ERROR] Agent Core streaming error: {agent_error}",
                    exc_info=True
                )

                # Check if error is recoverable
                if isinstance(agent_error, ConnectionError):
                    error_code = "AGENT_UNAVAILABLE"
                    message = "The AI service is temporarily unavailable, please try again later"
                else:
                    error_code = "AGENT_ERROR"
                    message = "Agent response failed, please try again"

                error_event = {
                    "type": "error",
                    "error_code": error_code,
                    "message": message,
                    "recoverable": True,
                }
                async for frame in _yield_sse("error", error_event):
                    yield frame
                return

            # Save assistant message after streaming completes
            try:
                if assistant_content:
                    await error_handler.retry_with_backoff(
                        service.add_message,
                        "save_assistant_message",
                        session_id=session_id,
                        user_id=user_id,
                        role="assistant",
                        content=assistant_content,
                    )
                    # Log to per-request memory
                    await req_memory.log_message(
                        session_id=session_id,
                        role="assistant",
                        content=assistant_content,
                    )
            except Exception as save_error:
                logger.error(f"[SAVE_ERROR] Failed to save assistant message: {save_error}")

                # Queue message for later retry
                queue_id = error_handler.queue_message_for_retry(
                    session_id=session_id,
                    user_id=user_id,
                    role="assistant",
                    content=assistant_content,
                )

                # Still send completion - we have the content, just not saved yet
                warning_event = {
                    "type": "warning",
                    "code": "MESSAGE_SAVE_DEFERRED",
                    "message": "Message saved locally but server persistence delayed",
                    "queue_id": queue_id,
                }
                async for frame in _yield_sse("warning", warning_event):
                    yield frame

            # Send completion event
            done_event = {
                "type": "done",
                "message_id": message_id,
                "tokens": len(assistant_content.split()),
            }
            async for frame in _yield_sse("done", done_event):
                yield frame

        except Exception as e:
            logger.error(f"[STREAMING_ERROR] Unexpected error: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred, please try again",
                "recoverable": False,
            }
            async for frame in _yield_sse("error", error_event):
                yield frame
        finally:
            if agent_stream is not None and hasattr(agent_stream, "aclose"):
                await agent_stream.aclose()
            if agent_core is not None:
                await agent_core.close()
            # CLEANUP: Per-request memory cleanup (guarantees isolation)
            try:
                await req_memory.cleanup()
                logger.debug(f"[STREAM] Memory cleanup completed for session {session_id}")
            except Exception as cleanup_error:
                logger.warning(f"[STREAM] Memory cleanup error: {cleanup_error}")
                # Log but don't fail - cleanup errors shouldn't break request

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
            "Content-Encoding": "identity",  # Don't compress SSE
            "X-Content-Type-Options": "nosniff",
        },
    )
