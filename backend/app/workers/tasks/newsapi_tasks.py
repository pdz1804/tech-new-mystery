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


DEFAULT_NEWSAPI_QUERY = (
    "(artificial intelligence OR AI OR machine learning OR LLM OR generative AI OR "
    "deep learning OR neural networks OR transformers OR embeddings OR "
    "AWS OR Azure OR cloud computing OR "
    "tech startup OR funding OR innovation OR breakthrough)"
)

# NewsAPI source IDs (must use exact IDs from NewsAPI sources endpoint)
DEFAULT_NEWSAPI_SOURCES = ["techcrunch", "the-verge", "google-news"]


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def newsapi_scheduled_task(self, from_date: str | None = None, query: str | None = None):
    """Scheduled task to discover articles via NewsAPI every 6 hours.

    Searches tech & AI topics from top 3 sources and stores results as pending searches for admin review.

    Args:
        from_date: Optional ISO format date (YYYY-MM-DD) to search from.
                   If not provided, defaults to yesterday.
        query: Optional custom search query. If not provided, uses comprehensive default.
    """
    logger.info("[NEWSAPI_SCHEDULED] Task started - executing async search")
    try:
        result = asyncio.run(_fetch_and_store_search_results(from_date=from_date, query=query))
        logger.info(f"[NEWSAPI_SCHEDULED] Task completed successfully: {result}")
        return result
    except Exception as exc:
        logger.error(f"[NEWSAPI_SCHEDULED] Task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


async def _fetch_and_store_search_results(
    from_date: str | None = None,
    query: str | None = None,
) -> dict:
    """Fetch news articles from NewsAPI's top 3 sources and store as pending searches."""
    from datetime import datetime, timedelta

    logger.info("[NEWSAPI_SCHEDULED] Starting scheduled NewsAPI article discovery")

    # Get date for search (use provided date or yesterday)
    if from_date:
        search_date = from_date
        logger.info(f"[NEWSAPI_SCHEDULED] Using provided date: {search_date}")
    else:
        search_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"[NEWSAPI_SCHEDULED] Using yesterday's date: {search_date}")

    search_query = (query or DEFAULT_NEWSAPI_QUERY).strip()
    if not search_query:
        search_query = DEFAULT_NEWSAPI_QUERY
    logger.info(f"[NEWSAPI_SCHEDULED] Search query: {search_query}")
    logger.info(f"[NEWSAPI_SCHEDULED] Sources: {DEFAULT_NEWSAPI_SOURCES}")

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

        # PHASE 1: Search each top source (5 results per source) - STRICT SOURCE LIMITING
        logger.info("[NEWSAPI_SCHEDULED] PHASE 1: Searching specific sources (TechCrunch, The Verge, Google News)")
        for source in DEFAULT_NEWSAPI_SOURCES:
            if results_found >= max_results_per_run:
                logger.info(f"[NEWSAPI_SCHEDULED] Reached max results ({max_results_per_run}) for this run")
                break

            logger.info(f"[NEWSAPI_SCHEDULED] Searching from source: {source}")

            try:
                # Search via NewsAPI with STRICT source filter (only this source, no fallback)
                search_result = await search_service.newsapi_search(
                    query=search_query,
                    limit=5,  # Get exactly 5 results per source
                    from_date=search_date,  # Only news from specified date
                    sort_by="popularity",  # Sort by popularity
                    sources=[source],  # STRICT: Only search this specific source
                )

                if not search_result.get("success"):
                    logger.error(f"[NEWSAPI_SCHEDULED] Search failed for source '{source}': {search_result.get('error')}")
                    continue

                results_count = len(search_result.get("results", []))
                logger.info(f"[NEWSAPI_SCHEDULED] Source '{source}': Found {results_count} articles")

                if not search_result.get("results"):
                    logger.warning(f"[NEWSAPI_SCHEDULED] No results for source: {source}")
                    continue

                # Save each search result as pending
                for result in search_result.get("results", []):
                    if results_found >= max_results_per_run:
                        break

                    url = result.get("url")
                    if not url:
                        logger.warning("Search result missing URL, skipping")
                        continue

                    # Check for duplicates (both in DB and current run)
                    if url in existing_urls:
                        logger.info(f"[NEWSAPI_SCHEDULED] ⊘ Duplicate URL skipped from {source}: {url}")
                        duplicates_skipped += 1
                        continue

                    try:
                        # Create pending search record
                        search_id = str(uuid.uuid4())
                        search_data = {
                            "search_id": search_id,
                            "query": search_query,
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
                logger.error(f"Error searching source '{source}': {str(e)}")
                continue

        # PHASE 2: Fallback - If we didn't get enough results from source-limited search, search without source restriction
        if results_found < max_results_per_run:
            logger.info(f"[NEWSAPI_SCHEDULED] PHASE 2: Fallback search (found {results_found}/{max_results_per_run} articles)")
            remaining_needed = max_results_per_run - results_found

            try:
                logger.info(f"[NEWSAPI_SCHEDULED] Searching without source restrictions for {remaining_needed} more articles")
                search_result = await search_service.newsapi_search(
                    query=search_query,
                    limit=remaining_needed,  # Get remaining articles needed
                    from_date=search_date,  # Only news from specified date
                    sort_by="popularity",  # Sort by popularity
                    sources=None,  # NO SOURCE FILTER - get from any source
                )

                if search_result.get("success") and search_result.get("results"):
                    fallback_results = len(search_result.get("results", []))
                    logger.info(f"[NEWSAPI_SCHEDULED] Fallback search found {fallback_results} additional articles")

                    for result in search_result.get("results", []):
                        if results_found >= max_results_per_run:
                            break

                        url = result.get("url")
                        if not url:
                            logger.warning("Fallback result missing URL, skipping")
                            continue

                        # Check for duplicates (both in DB and current run)
                        if url in existing_urls:
                            logger.info(f"[NEWSAPI_SCHEDULED] ⊘ Duplicate URL skipped from fallback: {url}")
                            duplicates_skipped += 1
                            continue

                        try:
                            # Create pending search record
                            search_id = str(uuid.uuid4())
                            search_data = {
                                "search_id": search_id,
                                "query": search_query,
                                "title": result.get("title", "Untitled"),
                                "url": url,
                                "snippet": result.get("description", "")[:500],  # Limit snippet length
                                "source": result.get("source", ""),  # May be from different sources now
                                "created_at": int(now_timestamp()),
                                "updated_at": int(now_timestamp()),
                            }

                            logger.debug(
                                f"[NEWSAPI_SCHEDULED] Creating fallback search result: {search_data['title']}"
                            )

                            # Save to pending searches
                            await search_repo.create(search_data)
                            logger.info(
                                f"[NEWSAPI_SCHEDULED] Saved fallback result: {search_id} - {search_data['title']}"
                            )
                            results_found += 1
                            existing_urls.add(url)

                        except Exception as e:
                            logger.error(f"Error saving fallback result {url}: {str(e)}")
                            continue
                else:
                    logger.warning("[NEWSAPI_SCHEDULED] Fallback search returned no results")

            except Exception as e:
                logger.error(f"[NEWSAPI_SCHEDULED] Fallback search failed: {str(e)}")

        summary = f"[NEWSAPI_SCHEDULED] ✓ COMPLETED | Found: {results_found} articles | Deduplicated: {duplicates_skipped} duplicates"
        logger.info(summary)

        return {
            "status": "success",
            "results_found": results_found,
            "duplicates_skipped": duplicates_skipped,
            "message": summary,
        }

    except Exception as e:
        logger.error(f"[NEWSAPI_SCHEDULED] Task failed: {str(e)}", exc_info=True)
        raise
