"""Chat endpoints."""

import asyncio
import inspect
import json
import logging
from datetime import datetime, timezone
import time
import uuid
from typing import AsyncGenerator

import re

import httpx
from jose import jwt
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.api.dependencies import get_request_agent_memory
from app.api.v1.chat.auth import get_chat_auth_user, validate_session_ownership
from app.api.v1.chat.schemas import (
    CreateSessionRequest,
    SessionResponse,
    MessageRequest,
    VoiceMessageRequest,
    VoiceSpeechRequest,
    VoiceLiveKitSessionRequest,
    VoiceEventRequest,
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
# 20ms between SSE frames — large enough for the OS to emit each event
# as a separate TCP segment so the browser receives them individually.
# 5ms was too short: multiple events could land in one network packet,
# causing the browser to see them all at once via a single reader.read().
SSE_FLUSH_PAUSE_SECONDS = 0.020
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
ELEVENLABS_SINGLE_USE_TOKEN_URL = "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe"


def _sse(event_type: str, data: dict) -> str:
    """Format a single Server-Sent Event."""
    payload = {
        **data,
        "_server_sent_at_ms": int(time.time() * 1000),
    }
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


def _speech_text(text: str) -> str:
    """Trim markdown-heavy assistant text into something pleasant to read aloud."""
    cleaned = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"[*_#>\-]{1,3}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:1200]


def _livekit_configured() -> bool:
    return bool(settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_livekit_token(
    *,
    room_name: str,
    user_id: str,
    session_id: str,
) -> str:
    now = int(time.time())
    metadata = {
        "app": "tech-news-mystery",
        "chat_session_id": session_id,
        "voice_stack": "livekit-elevenlabs-langchain",
        "agent_name": settings.livekit_agent_name,
        "stt_model": settings.elevenlabs_stt_model_id,
        "tts_model": settings.elevenlabs_tts_model_id,
        "langsmith_project": settings.langsmith_project,
    }
    claims = {
        "iss": settings.livekit_api_key,
        "sub": user_id,
        "nbf": now,
        "exp": now + settings.livekit_token_ttl_seconds,
        "name": "Tech News voice participant",
        "metadata": json.dumps(metadata),
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        },
    }
    return jwt.encode(claims, settings.livekit_api_secret or "", algorithm="HS256")


async def _trace_voice_event(
    *,
    name: str,
    user_id: str,
    inputs: dict,
    metadata: dict,
) -> str | None:
    """Best-effort LangSmith run creation for voice pipeline observability."""
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        return None

    run_id = str(uuid.uuid4())
    payload = {
        "id": run_id,
        "name": name,
        "run_type": "chain",
        "inputs": inputs,
        "start_time": _utc_now_iso(),
        "session_name": settings.langsmith_project,
        "extra": {
            "metadata": {
                **metadata,
                "user_id": user_id,
                "project": settings.langsmith_project,
                "voice_stack": "livekit-elevenlabs-langchain",
            },
        },
    }

    try:
        timeout = httpx.Timeout(5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.langsmith_endpoint.rstrip('/')}/runs",
                headers={
                    "x-api-key": settings.langsmith_api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        return run_id
    except Exception as exc:
        logger.warning("[VOICE] LangSmith trace event failed: %s", exc)
        return None


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


@router.post("/voice/speech")
async def synthesize_voice_speech(
    payload: VoiceSpeechRequest,
    current_user: dict = Depends(get_chat_auth_user),
) -> StreamingResponse:
    """Proxy ElevenLabs streaming TTS for chat voice mode.

    The API key stays server-side. If the key is not configured, the frontend can
    fall back to browser speech synthesis without affecting normal chat.
    """
    if not settings.elevenlabs_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ElevenLabs TTS is not configured",
        )

    text = _speech_text(payload.text)
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No speakable text provided",
        )

    url = ELEVENLABS_TTS_URL.format(voice_id=settings.elevenlabs_voice_id)
    params = {"output_format": settings.elevenlabs_tts_output_format}
    body = {
        "text": text,
        "model_id": settings.elevenlabs_tts_model_id,
        "voice_settings": {
            "stability": 0.48,
            "similarity_boost": 0.78,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    timeout = httpx.Timeout(settings.elevenlabs_timeout)
    client = httpx.AsyncClient(timeout=timeout)
    request = client.build_request(
        "POST",
        url,
        params=params,
        headers={
            "xi-api-key": settings.elevenlabs_api_key or "",
            "Content-Type": "application/json",
        },
        json=body,
    )

    try:
        response = await client.send(request, stream=True)
    except Exception as exc:
        await client.aclose()
        logger.error("[VOICE] ElevenLabs TTS connection error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice synthesis failed",
        )

    if response.status_code >= 400:
        detail = await response.aread()
        await response.aclose()
        await client.aclose()
        logger.warning(
            "[VOICE] ElevenLabs TTS failed status=%s body=%s",
            response.status_code,
            detail[:300],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice synthesis failed",
        )

    async def audio_stream() -> AsyncGenerator[bytes, None]:
        try:
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
        except Exception as exc:
            logger.error("[VOICE] ElevenLabs TTS proxy error: %s", exc, exc_info=True)
            return
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/voice/livekit-session")
async def create_voice_livekit_session(
    payload: VoiceLiveKitSessionRequest,
    current_user: dict = Depends(get_chat_auth_user),
) -> dict:
    """Create a LiveKit room token for the browser voice session."""
    if not _livekit_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit voice transport is not configured",
        )

    room_name = f"voice-{payload.session_id[:24]}-{uuid.uuid4().hex[:8]}"
    user_id = current_user["sub"]
    token = _create_livekit_token(
        room_name=room_name,
        user_id=user_id,
        session_id=payload.session_id,
    )
    trace_id = await _trace_voice_event(
        name="voice.livekit_session.created",
        user_id=user_id,
        inputs={"session_id": payload.session_id},
        metadata={
            "phase": "livekit_session_created",
            "transport": "livekit",
            "livekit_room": room_name,
            "livekit_agent_name": settings.livekit_agent_name,
        },
    )

    return {
        "success": True,
        "data": {
            "transport": "livekit",
            "server_url": settings.livekit_url,
            "room": room_name,
            "participant_token": token,
            "agent_name": settings.livekit_agent_name,
            "trace_id": trace_id,
            "expires_in": settings.livekit_token_ttl_seconds,
        },
    }


@router.post("/voice/events")
async def record_voice_event(
    payload: VoiceEventRequest,
    current_user: dict = Depends(get_chat_auth_user),
) -> dict:
    """Record voice pipeline telemetry in LangSmith when tracing is enabled."""
    trace_id = await _trace_voice_event(
        name=f"voice.{payload.phase}",
        user_id=current_user["sub"],
        inputs={
            "session_id": payload.session_id,
            "phase": payload.phase,
        },
        metadata={
            "phase": payload.phase,
            "provider": payload.provider,
            "transport": payload.transport,
            "livekit_room": payload.livekit_room,
            "transcript_chars": payload.transcript_chars,
            "output_chars": payload.output_chars,
            "latency_ms": payload.latency_ms,
        },
    )
    return {
        "success": True,
        "data": {
            "trace_id": trace_id,
            "tracing_enabled": bool(settings.langsmith_tracing and settings.langsmith_api_key),
        },
    }


@router.post("/voice/stt-token")
async def create_voice_stt_token(
    current_user: dict = Depends(get_chat_auth_user),
) -> dict:
    """Create a single-use ElevenLabs Realtime Scribe token for browser STT.

    The browser needs to open the ElevenLabs WebSocket directly for low-latency
    microphone streaming, but it must not receive the long-lived API key.
    """
    if not settings.elevenlabs_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ElevenLabs STT is not configured",
        )

    timeout = httpx.Timeout(settings.elevenlabs_timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                ELEVENLABS_SINGLE_USE_TOKEN_URL,
                headers={"xi-api-key": settings.elevenlabs_api_key},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("[VOICE] ElevenLabs STT token error: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Voice transcription token failed",
            )

    data = response.json()
    token = data.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice transcription token missing",
        )

    return {
        "success": True,
        "data": {
            "token": token,
            "model_id": settings.elevenlabs_stt_model_id,
            "audio_format": settings.elevenlabs_stt_audio_format,
        },
    }


@router.post("/voice/message")
async def send_voice_message(
    payload: VoiceMessageRequest,
    current_user: dict = Depends(get_chat_auth_user),
    req_memory: RequestAgentMemory = Depends(get_request_agent_memory),
) -> dict:
    """Send one voice turn and return a single final answer.

    Voice mode deliberately avoids frontend SSE rendering. The AgentCore runtime
    receives mode=voice, uses a short spoken-answer prompt, and returns one
    answer optimized for TTS latency.
    """
    error_handler = ErrorHandler()
    service = ChatService()
    user_id = current_user["sub"]
    started_at = time.perf_counter()

    try:
        InputValidator.validate_session_id(payload.session_id)
        InputValidator.validate_message_request(payload.content)
    except InvalidInputError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.user_message)

    session = await service.get_session(payload.session_id, user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice session not found")

    messages_result = await service.get_messages(payload.session_id, user_id, page_size=6)
    recent_events = [
        {
            "role": m["role"],
            "content": m["content"],
            "timestamp": m["timestamp"],
            "event_id": m["message_id"],
        }
        for m in messages_result["messages"]
    ]

    await req_memory.initialize(
        session_id=payload.session_id,
        user_id=user_id,
        recent_events=recent_events,
    )

    await error_handler.retry_with_backoff(
        service.add_message,
        "save_voice_user_message",
        session_id=payload.session_id,
        user_id=user_id,
        role="user",
        content=payload.content,
    )
    await req_memory.log_message(
        session_id=payload.session_id,
        role="user",
        content=payload.content,
    )

    assistant_content = ""
    agent_core: AgentCoreClient | None = None
    try:
        agent_core = AgentCoreClient()
        async for event in _iterate_with_timeout(
            agent_core.invoke_agent(
                session_id=payload.session_id,
                user_message=payload.content,
                context={
                    "recent_events": recent_events,
                    "request_scope": "voice",
                    "agent_mode": "voice",
                    "response_style": "one_spoken_paragraph",
                    "latency_priority": "high",
                },
                user_id=user_id,
                mode="voice",
            ),
            timeout=90.0,
        ):
            event_type = event.get("type")
            if event_type == "token":
                assistant_content += event.get("content", "")
            elif event_type == "error":
                raise RuntimeError(event.get("message") or "Voice agent response failed")

        assistant_content = assistant_content.strip()
        if not assistant_content:
            raise RuntimeError("Voice agent returned an empty response")

        await error_handler.retry_with_backoff(
            service.add_message,
            "save_voice_assistant_message",
            session_id=payload.session_id,
            user_id=user_id,
            role="assistant",
            content=assistant_content,
        )
        await req_memory.log_message(
            session_id=payload.session_id,
            role="assistant",
            content=assistant_content,
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Voice agent took too long, please try again.",
        )
    except Exception as exc:
        logger.error("[VOICE] Voice message failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice agent response failed",
        )
    finally:
        if agent_core is not None:
            await agent_core.close()
        await req_memory.cleanup()

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    await _trace_voice_event(
        name="voice.agent_turn.completed",
        user_id=user_id,
        inputs={"session_id": payload.session_id, "transcript_chars": len(payload.content)},
        metadata={
            "phase": "agent_turn_completed",
            "provider": "agentcore",
            "transport": "livekit",
            "output_chars": len(assistant_content),
            "latency_ms": latency_ms,
            "agent_mode": "voice",
            "streaming_disabled_for_latency": True,
        },
    )

    return {
        "success": True,
        "data": {
            "content": assistant_content,
            "latency_ms": latency_ms,
            "input_chars": len(payload.content),
            "output_chars": len(assistant_content),
        },
    }


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
        tool_calls_map: dict[str, dict] = {}  # tool_id -> tool_call dict for DynamoDB persistence
        message_segments: list[dict] = []
        current_text_segment_index: int | None = None
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
                        if token_content:
                            if current_text_segment_index is None:
                                current_text_segment_index = len(message_segments)
                                message_segments.append({"type": "text", "content": token_content})
                            else:
                                segment = message_segments[current_text_segment_index]
                                segment["content"] = f"{segment.get('content', '')}{token_content}"
                        logger.debug(f"[STREAM] Yielding token event, content_len={len(token_content)}")
                        async for frame in _yield_sse("token", event):
                            yield frame
                        if await request.is_disconnected():
                            logger.info("[STREAM] Client disconnected, stopping stream")
                            return

                    # Handle tool invocation events
                    elif event_type == "tool_invocation":
                        tool_id = event.get("tool_id", "")
                        tool_calls_map[tool_id] = {
                            "tool_id": tool_id,
                            "tool_name": event.get("tool_name", ""),
                            "status": "executing",
                            "args": event.get("tool_args"),
                        }
                        current_text_segment_index = None
                        message_segments.append({
                            "type": "tool",
                            "toolCall": tool_calls_map[tool_id],
                        })
                        logger.info("[STREAM] Tool invocation: %s id=%s", event.get("tool_name"), tool_id)
                        async for frame in _yield_sse("tool_invocation", event):
                            yield frame
                        if await request.is_disconnected():
                            logger.info("[STREAM] Client disconnected, stopping stream")
                            return

                    # Handle tool result events
                    elif event_type == "tool_result":
                        tool_id = event.get("tool_id", "")
                        status = event.get("status", "completed")
                        if tool_id in tool_calls_map:
                            tool_calls_map[tool_id].update({
                                "status": status,
                                "result": event.get("result_summary", ""),
                                "artifacts": event.get("result_artifacts", []),
                            })
                            updated_tool_call = tool_calls_map[tool_id]
                        else:
                            tool_calls_map[tool_id] = {
                                "tool_id": tool_id,
                                "tool_name": event.get("tool_name", ""),
                                "status": status,
                                "result": event.get("result_summary", ""),
                                "artifacts": event.get("result_artifacts", []),
                            }
                            updated_tool_call = tool_calls_map[tool_id]
                        for segment in message_segments:
                            if (
                                segment.get("type") == "tool"
                                and segment.get("toolCall", {}).get("tool_id") == tool_id
                            ):
                                segment["toolCall"] = updated_tool_call
                                break
                        logger.info("[STREAM] Tool result: %s id=%s status=%s", event.get("tool_name"), tool_id, status)
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
                            if current_text_segment_index is None:
                                current_text_segment_index = len(message_segments)
                                message_segments.append({"type": "text", "content": content})
                            else:
                                segment = message_segments[current_text_segment_index]
                                segment["content"] = f"{segment.get('content', '')}{content}"
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
                    tool_calls_json = json.dumps(list(tool_calls_map.values())) if tool_calls_map else None
                    segments_json = json.dumps(message_segments) if message_segments else None
                    await error_handler.retry_with_backoff(
                        service.add_message,
                        "save_assistant_message",
                        session_id=session_id,
                        user_id=user_id,
                        role="assistant",
                        content=assistant_content,
                        tool_calls_json=tool_calls_json,
                        segments_json=segments_json,
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
