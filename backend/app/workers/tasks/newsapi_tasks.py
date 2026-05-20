"""Scheduled tasks for NewsAPI article discovery.

Automatically searches tech topics via NewsAPI and stores results for admin review.
Admin approves results which then triggers scraping and article creation.
"""

import asyncio
import logging
import uuid
from app.workers.celery_app import celery_app
from app.repositories.pending_search_repository import PendingSearchRepository
from app.repositories.article_repository import ArticleRepository
from app.services.search_service import SearchService
from app.utils.time import now_timestamp

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def newsapi_scheduled_task(self):
    """Scheduled task to discover articles via NewsAPI every 6 hours.

    Searches tech topics and stores results as pending searches for admin review.
    """
    logger.info("[NEWSAPI_SCHEDULED] Task started - executing async search")
    try:
        result = asyncio.run(_fetch_and_store_search_results())
        logger.info(f"[NEWSAPI_SCHEDULED] Task completed successfully: {result}")
        return result
    except Exception as exc:
        logger.error(f"[NEWSAPI_SCHEDULED] Task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


async def _fetch_and_store_search_results() -> dict:
    """Fetch news articles from NewsAPI about tech from yesterday and store as pending searches."""
    from datetime import datetime, timedelta

    logger.info("[NEWSAPI_SCHEDULED] Starting scheduled NewsAPI article discovery")

    # Get yesterday's date for dynamic search
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(f"[NEWSAPI_SCHEDULED] Searching for news from {yesterday}")

    # Tech topics to search for news
    topics = [
        "artificial intelligence",
        "machine learning",
        "web development",
        "devops cloud computing",
        "cybersecurity",
        "blockchain cryptocurrency",
    ]

    search_repo = PendingSearchRepository()
    search_service = SearchService(ArticleRepository())

    results_found = 0
    duplicates_skipped = 0
    max_results_per_run = 15

    try:
        # Get existing search URLs to avoid duplicates
        existing_searches = await search_repo.list_pending(limit=1000)
        existing_urls = {s.url for s in existing_searches}
        logger.debug(f"Existing pending searches: {len(existing_urls)}")

        # Search each topic
        for topic in topics:
            if results_found >= max_results_per_run:
                logger.info(f"Reached max results ({max_results_per_run}) for this run")
                break

            logger.debug(f"Searching topic: {topic}")

            try:
                # Search via NewsAPI with news parameters
                search_result = await search_service.newsapi_search(
                    query=topic,
                    limit=5,  # Get 5 results per topic
                    from_date=yesterday,  # Only news from yesterday
                    sort_by="popularity",  # Sort by popularity
                )

                if not search_result.get("success"):
                    logger.error(f"[NEWSAPI_SCHEDULED] Search failed for topic '{topic}': {search_result.get('error')}")
                    continue

                if not search_result.get("results"):
                    logger.warning(f"[NEWSAPI_SCHEDULED] No results for topic: {topic}")
                    continue

                # Save each search result as pending
                for result in search_result.get("results", []):
                    if results_found >= max_results_per_run:
                        break

                    url = result.get("url")
                    if not url:
                        logger.warning("Search result missing URL, skipping")
                        continue

                    # Check for duplicates
                    if url in existing_urls:
                        logger.debug(f"Duplicate URL found, skipping: {url}")
                        duplicates_skipped += 1
                        continue

                    try:
                        # Create pending search record
                        search_id = str(uuid.uuid4())
                        search_data = {
                            "search_id": search_id,
                            "query": topic,
                            "title": result.get("title", "Untitled"),
                            "url": url,
                            "snippet": result.get("description", "")[:500],  # Limit snippet length
                            "source": result.get("source", ""),
                            "created_at": int(now_timestamp()),
                            "updated_at": int(now_timestamp()),
                        }

                        logger.debug(
                            f"[NEWSAPI_SCHEDULED] Creating pending search: {search_data['title']}"
                        )

                        # Save to pending searches
                        await search_repo.create(search_data)
                        logger.info(
                            f"[NEWSAPI_SCHEDULED] Saved search result: {search_id} - {search_data['title']}"
                        )
                        results_found += 1
                        existing_urls.add(url)

                    except Exception as e:
                        logger.error(f"Error saving search result {url}: {str(e)}")
                        continue

            except Exception as e:
                logger.error(f"Error searching topic '{topic}': {str(e)}")
                continue

        logger.info(
            f"[NEWSAPI_SCHEDULED] Completed: results_found={results_found}, duplicates_skipped={duplicates_skipped}"
        )

        return {
            "status": "success",
            "results_found": results_found,
            "duplicates_skipped": duplicates_skipped,
        }

    except Exception as e:
        logger.error(f"[NEWSAPI_SCHEDULED] Task failed: {str(e)}", exc_info=True)
        raise
