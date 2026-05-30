"""Celery tasks for article embedding indexing in Qdrant."""

import asyncio
import logging
from typing import Optional

from app.workers.celery_app import celery_app
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def index_article_task(
    self,
    article_id: str,
    slug: str,
    title: str,
    summary: Optional[str],
    content: str,
    category: Optional[str],
    author: Optional[str],
    published_at: Optional[str],
    view_count: int,
    source_id: str,
) -> dict:
    """Index article in Qdrant (guaranteed to complete via Celery worker).

    This task is queued when articles are created/updated, ensuring embeddings
    are generated and stored in Qdrant even if the HTTP request exits early.

    Args:
        article_id: Article ID (UUID)
        slug: Article slug
        title: Article title
        summary: Article summary
        content: Article content
        category: Article category
        author: Article author
        published_at: Publication timestamp
        view_count: View count
        source_id: Source ID

    Returns:
        Result dict with success status
    """
    try:
        logger.info(f"[EMBEDDING] Starting indexing for article {article_id}")

        qdrant_service = QdrantService()

        # Run async operation in sync context
        result = asyncio.run(
            qdrant_service.index_article(
                article_id=article_id,
                slug=slug,
                title=title,
                summary=summary,
                content=content,
                category=category,
                author=author,
                published_at=published_at,
                view_count=view_count,
                source_id=source_id,
            )
        )

        logger.info(f"[EMBEDDING] ✅ Article {article_id} indexed successfully to Qdrant")
        return {
            "success": True,
            "article_id": article_id,
            "message": f"Article {article_id} indexed to Qdrant",
        }

    except Exception as exc:
        logger.error(
            f"[EMBEDDING] ❌ Failed to index article {article_id}: {str(exc)}",
            exc_info=True
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def backfill_embeddings_task(self) -> dict:
    """Backfill embeddings for all articles without embeddings in Qdrant.

    This scans DynamoDB for all articles and ensures they have embeddings
    in Qdrant. Used for one-time backfill after embedding system fixes.

    Returns:
        Result dict with backfill statistics
    """
    try:
        import asyncio
        from app.services.article_service import ArticleService
        from app.services.qdrant_service import QdrantService
        from app.repositories.article_repository import ArticleRepository

        logger.info("[BACKFILL] Starting embeddings backfill for all articles")

        # Get all articles from DynamoDB
        article_repo = ArticleRepository()
        qdrant_service = QdrantService()

        # Scan all articles from DynamoDB
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            articles, _ = loop.run_until_complete(article_repo.list_all(limit=1000))
        finally:
            loop.close()

        total = len(articles)
        indexed = 0
        failed = []

        logger.info(f"[BACKFILL] Found {total} articles in DynamoDB, indexing...")

        for article in articles:
            try:
                # Index article
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        qdrant_service.index_article(
                            article_id=article.article_id,
                            slug=article.slug,
                            title=article.title,
                            summary=article.summary,
                            content=article.content,
                            category=article.category,
                            author=article.author,
                            published_at=article.published_at,
                            view_count=article.view_count,
                            source_id=article.source_id,
                        )
                    )
                    indexed += 1
                    logger.info(f"[BACKFILL] ✅ Indexed {indexed}/{total}")
                finally:
                    loop.close()

            except Exception as e:
                logger.warning(f"[BACKFILL] Failed to index {article.article_id}: {e}")
                failed.append(article.article_id)

        logger.info(f"[BACKFILL] ✅ Completed: {indexed}/{total} articles indexed")

        return {
            "success": True,
            "total": total,
            "indexed": indexed,
            "failed": len(failed),
            "failed_ids": failed,
        }

    except Exception as exc:
        logger.error(f"[BACKFILL] ❌ Backfill failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def delete_embedding_task(self, article_id: str) -> dict:
    """Delete article embedding from Qdrant when article is deleted.

    Args:
        article_id: Article ID to delete from Qdrant

    Returns:
        Result dict with success status
    """
    try:
        logger.info(f"[EMBEDDING] Deleting embedding for article {article_id}")

        qdrant_service = QdrantService()

        # Run async operation - use delete_article to remove from Qdrant
        asyncio.run(qdrant_service.delete_article(article_id))

        logger.info(f"[EMBEDDING] ✅ Embedding deleted for article {article_id}")
        return {
            "success": True,
            "article_id": article_id,
            "message": f"Embedding deleted for article {article_id}",
        }

    except Exception as exc:
        logger.error(
            f"[EMBEDDING] ❌ Failed to delete embedding for {article_id}: {str(exc)}",
            exc_info=True
        )
        raise self.retry(exc=exc)
