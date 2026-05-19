"""Search request/response schemas."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request."""

    query: str = Field(..., min_length=1, max_length=500)
    category: str | None = None
    source_id: str | None = None
    limit: int = 20


class SearchResultResponse(BaseModel):
    """Search result response."""

    success: bool = True
    data: list[dict] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
