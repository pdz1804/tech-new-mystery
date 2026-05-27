"""Article request/response schemas."""

from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from datetime import datetime


class ArticleBase(BaseModel):
    """Base article schema."""

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    summary: str | None = None
    category: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CreateArticleRequest(BaseModel):
    """Create article request."""

    title: str = Field(..., min_length=1, max_length=500)
    original_url: HttpUrl
    content: str
    source_id: str


class UpdateArticleRequest(BaseModel):
    """Update article request."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = None
    author: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    summary: str | None = None

    def model_post_init(self, __context):
        """Validate that at least one field is provided."""
        fields_provided = [
            self.title,
            self.content,
            self.author,
            self.category,
            self.tags,
            self.summary,
        ]
        if not any(f is not None for f in fields_provided):
            raise ValueError("At least one field must be provided for update")


class CreateArticleFromUrlRequest(BaseModel):
    """Create article from URL request."""

    url: HttpUrl
    title: str | None = Field(None, min_length=1, max_length=500)
    author: str | None = None
    auto_summarize: bool = True


class DeleteResponse(BaseModel):
    """Delete response."""

    success: bool
    message: str


class ArticleResponse(ArticleBase):
    """Article response."""

    article_id: str
    content: str | None = None
    markdown_content: str | None = None
    author: str | None = None
    original_url: str
    source_id: str
    preview_image: str | None = None
    quality_score: float | None = None
    view_count: int
    is_published: bool
    published_at: datetime | None = None
    created_at: datetime


class ArticleDetailResponse(BaseModel):
    """Article detail response."""

    success: bool = True
    data: ArticleResponse


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    limit: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether more items exist")
    next_cursor: str | None = Field(None, description="Cursor for next page (if has_next=true)")
    total_count: int | None = Field(None, description="Total items available (optional)")


class ArticleListResponse(BaseModel):
    """Article list response with proper pagination."""

    success: bool = True
    data: list[ArticleResponse]
    meta: PaginationMeta


class SummarizationResponse(BaseModel):
    """Summarization task response."""

    success: bool
    article_id: str
    summary: str | None = None
    category: str | None = None
    status: str = "processing"
    message: str | None = None
