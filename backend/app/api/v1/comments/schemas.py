"""Comment request/response schemas."""

from pydantic import BaseModel, Field, ConfigDict


class CreateCommentRequest(BaseModel):
    """Create comment request."""

    content: str = Field(..., min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    """Comment response."""

    model_config = ConfigDict(from_attributes=True)

    comment_id: str
    user_id: str
    content: str
    created_at: str


class CommentListResponse(BaseModel):
    """Comment list response."""

    success: bool = True
    data: list[CommentResponse]
    meta: dict = Field(default_factory=dict)
