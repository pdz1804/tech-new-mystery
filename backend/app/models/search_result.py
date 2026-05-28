"""Search result schema for semantic search tool."""

from pydantic import BaseModel
from typing import Optional


class ArticleResult(BaseModel):
    """Result schema for article search operations.

    Represents a single search result with article metadata and relevance scoring.
    """
    article_id: str
    title: str
    summary: str
    relevance_score: float
    source: str
    url: str
    published_at: Optional[int] = None
    author: Optional[str] = None
    category: Optional[str] = None
    view_count: int = 0
    engagement_score: float = 0.0

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "article_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Breaking: New AI Model Revolutionizes Tech",
                "summary": "A groundbreaking AI model has been released...",
                "relevance_score": 0.95,
                "source": "techcrunch",
                "url": "https://techcrunch.com/article/...",
                "published_at": 1685049600,
                "author": "Jane Doe",
                "category": "AI",
                "view_count": 1234,
                "engagement_score": 0.87,
            }
        }
