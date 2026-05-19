"""Trending Articles business logic service."""

from app.repositories.trending_repository import TrendingRepository
from app.repositories.article_repository import ArticleRepository
from app.utils.time import timestamp_to_datetime


class TrendingService:
    """Trending service for business logic."""

    def __init__(self, trending_repo: TrendingRepository) -> None:
        """Initialize service."""
        self._trending_repo = trending_repo
        self._article_repo = ArticleRepository()

    async def get_trending_articles(self, limit: int = 20) -> list[dict]:
        """Get trending articles with full article details."""
        trending_items = await self._trending_repo.get_trending(limit=limit)
        articles = []

        for trending_item in trending_items:
            article = await self._article_repo.get_by_id(trending_item.article_id)
            if article:
                articles.append(
                    {
                        "article_id": article.article_id,
                        "title": article.title,
                        "slug": article.slug,
                        "summary": article.summary,
                        "original_url": article.original_url,
                        "source_id": article.source_id,
                        "category": article.category,
                        "tags": article.tags,
                        "view_count": article.view_count,
                        "is_published": article.is_published,
                        "published_at": timestamp_to_datetime(article.published_at) if article.published_at else None,
                        "created_at": timestamp_to_datetime(article.created_at) if article.created_at else None,
                    }
                )

        return articles

    async def recalculate_trending(self) -> None:
        """Recalculate trending scores."""
        pass
