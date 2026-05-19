"""News source request/response schemas."""

from pydantic import BaseModel, Field, ConfigDict, HttpUrl


class NewsSourceBase(BaseModel):
    """Base news source schema."""

    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    category: str | None = None
    priority: int = Field(5, ge=1, le=10)
    enabled: bool = True


class CreateNewsSourceRequest(NewsSourceBase):
    """Create news source request."""

    pass


class NewsSourceResponse(NewsSourceBase):
    """News source response."""

    model_config = ConfigDict(from_attributes=True)

    source_id: str
    created_at: str
