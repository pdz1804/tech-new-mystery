"""Crawling tasks."""

import logging
import uuid
from datetime import datetime
from slugify import slugify

from app.integrations.crawler_client import get_crawler_client
from app.repositories.article_repository import ArticleRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.utils.time import now_timestamp
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def daily_crawl_task(self) -> dict:
    """Daily news crawl task - crawl all enabled news sources."""
    try:
        import asyncio

        return asyncio.run(_crawl_all_sources())
    except Exception as exc:
        logger.error(f"Daily crawl task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def crawl_single_source_task(self, source_id: str) -> dict:
    """Crawl a single news source."""
    try:
        import asyncio

        return asyncio.run(_crawl_source(source_id))
    except Exception as exc:
        logger.error(f"Single source crawl failed for {source_id}: {exc}")
        raise self.retry(exc=exc)


async def _crawl_all_sources() -> dict:
    """Internal async function to crawl all sources."""
    try:
        source_repo = NewsSourceRepository()
        article_repo = ArticleRepository()
        crawler = await get_crawler_client()

        # Get all enabled sources
        sources = await source_repo.list_all()
        enabled_sources = [s for s in sources if s.enabled]

        logger.info(f"Starting daily crawl of {len(enabled_sources)} sources")

        results = {
            "total": len(enabled_sources),
            "successful": 0,
            "failed": 0,
            "articles_created": 0,
            "articles_skipped": 0,
            "errors": [],
        }

        for source in enabled_sources:
            if not source.url:
                logger.warning(f"Source {source.name} has no URL")
                results["failed"] += 1
                continue

            try:
                logger.info(f"Crawling source: {source.name} ({source.url})")
                crawled = await crawler.crawl_url(source.url, timeout=60)  # 60s for browser init + load

                if not crawled.success:
                    logger.warning(f"Failed to crawl {source.name}: {crawled.error}")
                    results["failed"] += 1
                    results["errors"].append(
                        {"source": source.name, "error": crawled.error}
                    )
                    continue

                # Check if article already exists by URL
                existing = await article_repo.get_by_slug(
                    slugify(crawled.url)
                )
                if existing:
                    logger.info(f"Article already exists for URL: {crawled.url}")
                    results["articles_skipped"] += 1
                    results["successful"] += 1
                    continue

                # Create article from crawled content
                article_data = {
                    "article_id": str(uuid.uuid4()),
                    "title": crawled.title or "Untitled",
                    "slug": slugify(crawled.title or crawled.url),
                    "source_id": source.source_id,
                    "original_url": crawled.url,
                    "content": crawled.content,
                    "markdown_content": crawled.markdown,
                    "author": None,
                    "category": source.category or "General",
                    "tags": [],
                    "is_published": True,
                    "published_at": now_timestamp(),
                }

                article = await article_repo.create(article_data)
                logger.info(
                    f"Created article: {article.title} (ID: {article.article_id})"
                )
                results["articles_created"] += 1
                results["successful"] += 1

            except Exception as e:
                logger.error(f"Error processing source {source.name}: {e}")
                results["failed"] += 1
                results["errors"].append({"source": source.name, "error": str(e)})
                continue

        logger.info(
            f"Daily crawl completed: {results['successful']} sources processed, "
            f"{results['articles_created']} articles created, "
            f"{results['articles_skipped']} skipped"
        )
        return results

    except Exception as e:
        logger.error(f"Error in daily crawl: {e}")
        raise


async def _crawl_source(source_id: str) -> dict:
    """Internal async function to crawl a single source."""
    try:
        source_repo = NewsSourceRepository()
        article_repo = ArticleRepository()
        crawler = await get_crawler_client()

        # Get source
        source = await source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source {source_id} not found")
            return {"success": False, "error": f"Source {source_id} not found"}

        if not source.url:
            logger.warning(f"Source {source_id} has no URL")
            return {"success": False, "error": f"Source {source_id} has no URL"}

        logger.info(f"Crawling source: {source.name}")

        crawled = await crawler.crawl_url(source.url, timeout=60)  # 60s for browser init + load
        if not crawled.success:
            logger.error(f"Failed to crawl {source.name}: {crawled.error}")
            return {"success": False, "error": crawled.error, "source_id": source_id}

        # Check if article already exists
        existing = await article_repo.get_by_slug(slugify(crawled.url))
        if existing:
            logger.info(f"Article already exists for URL: {crawled.url}")
            return {
                "success": True,
                "source_id": source_id,
                "article_id": existing.article_id,
                "status": "skipped",
                "reason": "Article already exists",
            }

        # Create article from crawled content
        article_data = {
            "article_id": str(uuid.uuid4()),
            "title": crawled.title or "Untitled",
            "slug": slugify(crawled.title or crawled.url),
            "source_id": source.source_id,
            "original_url": crawled.url,
            "content": crawled.content,
            "markdown_content": crawled.markdown,
            "author": None,
            "category": source.category or "General",
            "tags": [],
            "is_published": True,
            "published_at": now_timestamp(),
        }

        article = await article_repo.create(article_data)
        logger.info(f"Successfully crawled and created article: {article.title}")
        return {
            "success": True,
            "source_id": source_id,
            "article_id": article.article_id,
            "title": article.title,
            "content_length": len(article.content),
        }

    except Exception as e:
        logger.error(f"Error crawling source {source_id}: {e}")
        raise
