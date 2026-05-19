"""Trending articles tasks."""

import asyncio
import logging
import time

from app.repositories.article_repository import ArticleRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.user_saves_repository import UserSavesRepository
from app.repositories.trending_repository import TrendingRepository
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def recalculate_trending_task(self) -> dict:
    """Celery task to recalculate trending articles scores.

    Runs every 30 minutes via Beat scheduler.
    """
    try:
        return asyncio.run(_recalculate_trending())
    except Exception as exc:
        logger.error(f"Trending calculation task failed: {exc}")
        return {
            "success": False,
            "error": str(exc),
        }


async def _calculate_trending_score(
    views: int,
    comments: int,
    saves: int,
) -> float:
    """Calculate trending score for an article.

    Uses weighted average:
    - Views: 40% weight
    - Comments: 35% weight
    - Saves: 25% weight
    """
    score = (views * 0.4) + (comments * 0.35) + (saves * 0.25)
    return score


async def _get_article_comments_count(article_id: str) -> int:
    """Get count of comments for an article."""
    try:
        comment_repo = CommentRepository()
        comments = await comment_repo.get_by_article(article_id, limit=1000)
        return len(comments) if comments else 0
    except Exception:
        return 0


async def _get_article_saves_count(article_id: str) -> int:
    """Get count of saves for an article.

    Note: This does a full table scan since UserSavesModel is keyed by
    (user_id, article_id). For large tables, consider adding a GSI.
    """
    try:
        # For MVP, we'll estimate based on available data
        # In production, add a GSI on article_id for efficient querying
        return 0  # Placeholder - would need GSI to efficiently count
    except Exception:
        return 0


async def _recalculate_trending() -> dict:
    """Internal async function to calculate trending articles.

    Returns:
        dict: Result with total, successful, failed, articles_ranked, errors
    """
    article_repo = ArticleRepository()
    trending_repo = TrendingRepository()

    result = {
        "success": True,
        "total": 0,
        "successful": 0,
        "failed": 0,
        "articles_ranked": [],
        "errors": [],
    }

    try:
        logger.info("Starting trending calculation")

        # Get all published articles
        articles, _ = await article_repo.list_all(limit=1000)
        if not articles:
            logger.info("No articles found for trending calculation")
            result["total"] = 0
            return result

        # Filter to published articles only
        published_articles = [
            a for a in articles
            if getattr(a, "is_published", False)
        ]
        result["total"] = len(published_articles)

        if not published_articles:
            logger.info("No published articles found")
            return result

        logger.info(f"Processing {len(published_articles)} published articles")

        # Calculate scores for each article
        article_scores = []

        for article in published_articles:
            try:
                article_id = article.article_id
                views = getattr(article, "view_count", 0) or 0

                # Get comments and saves counts
                comments = await _get_article_comments_count(article_id)
                saves = await _get_article_saves_count(article_id)

                # Calculate trending score
                score = await _calculate_trending_score(
                    views, comments, saves
                )

                article_scores.append({
                    "article_id": article_id,
                    "title": getattr(article, "title", "Unknown"),
                    "score": score,
                    "views": views,
                    "comments": comments,
                    "saves": saves,
                })
                result["successful"] += 1

            except Exception as e:
                result["failed"] += 1
                result["errors"].append({
                    "article_id": getattr(article, "article_id", "unknown"),
                    "error": str(e),
                })
                logger.error(f"Error processing article {getattr(article, 'article_id', 'unknown')}: {e}")

        # Sort by score descending and assign ranks
        article_scores.sort(key=lambda x: x["score"], reverse=True)

        # Get top 50 trending articles
        top_articles = article_scores[:50]

        # Save trending records
        current_time = int(time.time())
        for rank, item in enumerate(top_articles, start=1):
            try:
                trending_id = f"trending-{item['article_id']}"

                await trending_repo.update_trending_score(
                    article_id=item["article_id"],
                    score=item["score"],
                    rank=rank,
                    trending_id=trending_id,
                    calculated_at=current_time,
                )

                result["articles_ranked"].append({
                    "rank": rank,
                    "article_id": item["article_id"],
                    "title": item["title"],
                    "score": item["score"],
                })

            except Exception as e:
                result["errors"].append({
                    "article_id": item["article_id"],
                    "error": f"Failed to save trending record: {str(e)}",
                })
                logger.error(f"Error saving trending record: {e}")

        logger.info(f"Trending calculation complete: {len(result['articles_ranked'])} articles ranked")
        return result

    except Exception as e:
        logger.error(f"Error calculating trending: {e}")
        result["success"] = False
        result["error"] = str(e)
        return result
