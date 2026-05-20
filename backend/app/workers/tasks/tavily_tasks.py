"""Scheduled tasks for Tavily article fetching.

Automatically fetches tech articles via Tavily on a schedule and stores them
as pending articles for admin review and approval.
"""

import asyncio
import logging
from app.workers.celery_app import celery_app
from app.repositories.article_repository import ArticleRepository
from app.services.article_service import ArticleService
from app.services.article_processing_service import ArticleProcessingService
from app.services.scraping_service import ScrapingService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def tavily_scheduled_task(self):
    """Scheduled task to fetch articles via Tavily every 6 hours.

    Searches tech topics and creates pending articles for admin review.
    Articles are created with is_published=False and source_id='tavily-scheduled'.

    Returns:
        dict with status and counts
    """
    try:
        return asyncio.run(_fetch_and_store_articles())
    except Exception as exc:
        logger.error(f"Tavily task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


async def _fetch_and_store_articles() -> dict:
    """Fetch articles from Tavily and store as pending."""
    logger.info("[TAVILY_SCHEDULED] Starting scheduled Tavily article fetch")

    # Tech topics to search
    topics = [
        "artificial intelligence",
        "machine learning",
        "web development",
        "devops cloud computing",
        "cybersecurity",
        "blockchain cryptocurrency",
    ]

    article_repo = ArticleRepository()
    search_service = SearchService(article_repo)
    scraper = ScrapingService()
    processor = ArticleProcessingService()

    articles_created = 0
    articles_failed = 0
    duplicates_skipped = 0
    max_articles_per_run = 5

    try:
        # Get existing URLs to avoid duplicates
        existing_articles, _ = await article_repo.list_all(limit=2000)
        existing_urls = {a.original_url for a in existing_articles}
        logger.debug(f"Existing articles in system: {len(existing_urls)}")

        # Search each topic
        for topic in topics:
            if articles_created >= max_articles_per_run:
                logger.info(f"Reached max articles ({max_articles_per_run}) for this run")
                break

            logger.debug(f"Searching topic: {topic}")

            try:
                # Search via Tavily
                search_result = await search_service.tavily_search(
                    query=topic,
                    limit=3,  # Get 3 results per topic
                )

                if not search_result.get("success") or not search_result.get("results"):
                    logger.warning(f"No results for topic: {topic}")
                    continue

                # Process each search result
                for result in search_result.get("results", [])[:3]:
                    if articles_created >= max_articles_per_run:
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
                        logger.debug(f"Processing article from: {url}")

                        # Scrape the article
                        scrape_result = await scraper.scrape_url(url)

                        if not scrape_result.get("success"):
                            logger.warning(f"Failed to scrape {url}: {scrape_result.get('error')}")
                            articles_failed += 1
                            continue

                        raw_content = scrape_result.get("raw_html")
                        if not raw_content or len(raw_content.strip()) < 100:
                            logger.warning(f"Insufficient content from {url}")
                            articles_failed += 1
                            continue

                        # Extract image URLs for processing
                        import re
                        image_pattern = r'!\[.*?\]\((https://[^)]+)\)'
                        image_urls = re.findall(
                            image_pattern,
                            scrape_result.get("markdown_content", "")
                        )

                        logger.debug(f"Extracted {len(image_urls)} images from article")

                        # Process with AI
                        processing_result = await processor.process_url_content(
                            url=url,
                            raw_content=raw_content,
                            title=result.get("title"),
                            author=None,
                            image_urls=image_urls,
                        )

                        if not processing_result:
                            logger.warning(f"AI processing failed for {url}")
                            articles_failed += 1
                            continue

                        # Create article with is_published=False (pending state)
                        import uuid
                        from app.utils.slug import generate_slug
                        from app.utils.time import now_timestamp

                        article_id = str(uuid.uuid4())
                        generated_title = processing_result.get("title", "Untitled")
                        slug = generate_slug(generated_title)

                        article_data = {
                            "article_id": article_id,
                            "title": generated_title,
                            "slug": slug,
                            "source_id": "tavily-scheduled",  # Mark as Tavily-sourced
                            "original_url": url,
                            "content": processor._extract_text_from_html(raw_content),
                            "summary": processing_result.get("summary"),
                            "markdown_content": processing_result.get("structured_markdown"),
                            "author": None,
                            "category": processing_result.get("category", "Other"),
                            "tags": processing_result.get("tags", []),
                            "is_published": False,  # PENDING state
                        }

                        # Save to database
                        created_article = await article_repo.create(article_data)
                        logger.info(f"Created pending article: {article_id} - {generated_title}")
                        articles_created += 1
                        existing_urls.add(url)

                    except Exception as e:
                        logger.error(f"Error processing article {url}: {str(e)}")
                        articles_failed += 1
                        continue

            except Exception as e:
                logger.error(f"Error searching topic '{topic}': {str(e)}")
                continue

        logger.info(
            f"[TAVILY_SCHEDULED] Completed: "
            f"created={articles_created}, failed={articles_failed}, "
            f"duplicates_skipped={duplicates_skipped}"
        )

        return {
            "status": "success",
            "articles_created": articles_created,
            "articles_failed": articles_failed,
            "duplicates_skipped": duplicates_skipped,
        }

    except Exception as e:
        logger.error(f"[TAVILY_SCHEDULED] Task failed: {str(e)}", exc_info=True)
        raise
