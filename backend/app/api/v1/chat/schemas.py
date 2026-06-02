"""Chat request/response schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class CreateSessionRequest(BaseModel):
    """Create a chat session request."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class SessionResponse(BaseModel):
    """Chat session response."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    message_count: int = 0
    created_at: float
    updated_at: float
    last_message_at: float


class MessageRequest(BaseModel):
    """Chat message request."""

    content: str = Field(..., min_length=1, max_length=4000)


class VoiceSpeechRequest(BaseModel):
    """Convert assistant text to speech."""

    text: str = Field(..., min_length=1, max_length=1200)


class VoiceLiveKitSessionRequest(BaseModel):
    """Create a LiveKit voice transport session."""

    session_id: str = Field(..., min_length=1, max_length=255)


class VoiceEventRequest(BaseModel):
    """Record voice pipeline telemetry."""

    session_id: str = Field(..., min_length=1, max_length=255)
    phase: str = Field(..., min_length=1, max_length=80)
    provider: str = Field(default="elevenlabs", max_length=80)
    transport: str = Field(default="livekit", max_length=80)
    livekit_room: Optional[str] = Field(None, max_length=255)
    transcript_chars: Optional[int] = Field(None, ge=0)
    output_chars: Optional[int] = Field(None, ge=0)
    latency_ms: Optional[int] = Field(None, ge=0)


class UpdateSessionRequest(BaseModel):
    """Update session metadata request."""

    title: str = Field(..., min_length=1, max_length=255)


class MessageResponse(BaseModel):
    """Chat message response."""

    message_id: str
    session_id: str
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    token_count: Optional[int] = None
    model_used: Optional[str] = None
    tool_calls_json: Optional[str] = None  # JSON-serialized tool calls for history restore
    segments_json: Optional[str] = None  # Ordered text/tool segments for history restore


class SessionListResponse(BaseModel):
    """Session list response with metadata."""

    success: bool = True
    data: list[SessionResponse]
    meta: dict = Field(
        default_factory=lambda: {"page": 1, "limit": 20, "total": None, "last_key": None}
    )


class MessageListResponse(BaseModel):
    """Message list response with pagination."""

    success: bool = True
    data: list[MessageResponse]
    meta: dict = Field(
        default_factory=lambda: {"page": 1, "limit": 20, "total": None, "last_key": None}
    )


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = False
    error: str
    code: str


class StreamEventToken(BaseModel):
    """SSE token event."""

    type: str = "token"
    content: str


class StreamEventToolInvocation(BaseModel):
    """SSE tool invocation event."""

    type: str = "tool_invocation"
    tool_name: str
    tool_id: Optional[str] = None
    tool_args: Optional[dict] = None


class StreamEventToolResult(BaseModel):
    """SSE tool result event."""

    type: str = "tool_result"
    tool_name: str
    result_summary: Optional[str] = None
    status: str = "completed"


class StreamEventDone(BaseModel):
    """SSE done event (stream complete)."""

    type: str = "done"
    message_id: str
    tokens: int


class StreamEventError(BaseModel):
    """SSE error event."""

    type: str = "error"
    error: str
    code: str = "UNKNOWN_ERROR"
