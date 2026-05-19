"""Summarization tasks."""

import logging

from app.repositories.article_repository import ArticleRepository
from app.services.summarization_service import SummarizationService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def summarize_article_task(self, article_id: str) -> dict:
    """Summarize a single article using LLM."""
    try:
        import asyncio

        return asyncio.run(_summarize_article(article_id))
    except Exception as exc:
        logger.error(f"Summarization task failed for article {article_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def batch_summarize_task(self) -> dict:
    """Summarize all articles without summaries in batch."""
    try:
        import asyncio

        return asyncio.run(_batch_summarize())
    except Exception as exc:
        logger.error(f"Batch summarization task failed: {exc}")
        raise self.retry(exc=exc)


async def _summarize_article(article_id: str) -> dict:
    """Internal async function to summarize an article."""
    try:
        article_repo = ArticleRepository()
        service = SummarizationService(article_repo)

        logger.info(f"Summarizing article {article_id}")

        # Get article first
        article = await article_repo.get_by_id(article_id)
        if not article:
            logger.warning(f"Article {article_id} not found")
            return {"success": False, "error": "Article not found"}

        # Check if already has summary
        if article.summary:
            logger.info(f"Article {article_id} already has summary, skipping")
            return {
                "success": True,
                "article_id": article_id,
                "status": "skipped",
                "reason": "Already has summary",
            }

        # Generate summary
        summary = await service.summarize_article(article_id)
        if not summary:
            logger.warning(f"Failed to generate summary for article {article_id}")
            return {"success": False, "error": "Failed to generate summary"}

        # Extract citations
        citations = await service.extract_citations(article_id, summary)

        # Classify category
        category = await service.classify_category(article_id)

        # Save summary and category back to article
        await article_repo.update(
            article_id,
            summary=summary,
            category=category or article.category,
        )

        logger.info(f"Successfully summarized article {article_id}")
        return {
            "success": True,
            "article_id": article_id,
            "title": article.title,
            "summary_length": len(summary),
            "citations_count": len(citations),
            "category": category,
        }

    except Exception as e:
        logger.error(f"Error summarizing article {article_id}: {e}")
        raise


async def _batch_summarize() -> dict:
    """Internal async function to batch summarize articles."""
    try:
        article_repo = ArticleRepository()
        service = SummarizationService(article_repo)

        logger.info("Starting batch summarization task")

        # Get all articles without summaries
        articles, _ = await article_repo.list_all(limit=100)
        articles_to_summarize = [
            a for a in articles if not a.summary or a.summary.strip() == ""
        ]

        logger.info(f"Found {len(articles_to_summarize)} articles to summarize")

        if not articles_to_summarize:
            logger.info("No articles to summarize")
            return {
                "success": True,
                "total": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
            }

        # Summarize in batches
        results = {
            "total": len(articles_to_summarize),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        batch_size = 5
        for i in range(0, len(articles_to_summarize), batch_size):
            batch = articles_to_summarize[i : i + batch_size]
            logger.info(
                f"Processing batch {i // batch_size + 1} ({len(batch)} articles)"
            )

            for article in batch:
                try:
                    # Generate summary
                    summary = await service.summarize_article(
                        article.article_id,
                        max_tokens=300,
                        temperature=0.5,
                    )

                    if not summary:
                        logger.warning(f"Failed to summarize article {article.article_id}")
                        results["failed"] += 1
                        results["errors"].append(
                            {
                                "article_id": article.article_id,
                                "error": "Failed to generate summary",
                            }
                        )
                        continue

                    # Extract citations
                    citations = await service.extract_citations(
                        article.article_id, summary
                    )

                    # Classify category
                    category = await service.classify_category(article.article_id)

                    # Save to database
                    await article_repo.update(
                        article.article_id,
                        summary=summary,
                        category=category or article.category,
                    )

                    results["successful"] += 1
                    logger.info(
                        f"Summarized article {article.article_id} with category {category}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error processing article {article.article_id}: {e}"
                    )
                    results["failed"] += 1
                    results["errors"].append(
                        {"article_id": article.article_id, "error": str(e)}
                    )

        logger.info(
            f"Batch summarization completed: {results['successful']} successful, "
            f"{results['failed']} failed out of {results['total']} articles"
        )
        return results

    except Exception as e:
        logger.error(f"Error in batch summarization: {e}")
        raise
