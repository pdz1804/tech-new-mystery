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
