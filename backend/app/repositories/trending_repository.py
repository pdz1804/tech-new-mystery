"""Trending Articles data repository."""

import time

from app.models.trending_article import TrendingArticleModel


class TrendingRepository:
    """Trending articles repository for DynamoDB access."""

    async def get_trending(self, limit: int = 20) -> list[TrendingArticleModel]:
        """Get top trending articles.

        Args:
            limit: Maximum number of articles to return.

        Returns:
            List of trending articles sorted by rank.
        """
        try:
            # Scan the entire table and sort by rank
            items = TrendingArticleModel.scan()
            sorted_items = sorted(
                items,
                key=lambda x: getattr(x, "rank", float("inf"))
            )
            return sorted_items[:limit]
        except Exception:
            return []

    async def update_trending_score(
        self,
        article_id: str,
        score: float,
        rank: int,
        trending_id: str,
        calculated_at: int,
    ) -> TrendingArticleModel:
        """Update trending score for an article.

        Args:
            article_id: ID of the article.
            score: Calculated trending score.
            rank: Rank position (1-50).
            trending_id: Unique ID for this trending record.
            calculated_at: Timestamp when calculated.

        Returns:
            Updated trending article record.
        """
        current_time = int(time.time())

        item = TrendingArticleModel(
            trending_id=trending_id,
            article_id=article_id,
            score=score,
            rank=rank,
            calculated_at=calculated_at,
            updated_at=current_time,
        )

        item.save()
        return item

    async def get_by_id(self, trending_id: str) -> TrendingArticleModel | None:
        """Get trending article record by ID.

        Args:
            trending_id: ID of the trending record.

        Returns:
            Trending article record or None if not found.
        """
        try:
            return TrendingArticleModel.get(trending_id)
        except Exception:
            return None
