"""Celery app factory and beat schedule."""

import logging
from celery import Celery, signals
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "tech_news_mystery",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Increase heartbeat timeout - workers may be busy for 60+ seconds with Crawl4AI
    # Default is too short and causes "missed heartbeat" errors
    worker_heartbeat_interval=5,  # Send heartbeat every 5 seconds
    worker_heartbeat_timeout=300,  # Allow 5 minutes without heartbeat before declaring worker dead
    beat_schedule={
        "crawl-news-daily": {
            "task": "app.workers.tasks.crawl_tasks.daily_crawl_task",
            "schedule": crontab(hour=2, minute=0),
        },
        "recalculate-trending": {
            "task": "app.workers.tasks.trending_tasks.recalculate_trending_task",
            "schedule": crontab(minute="*/30"),
        },
        "fetch-tavily-articles": {
            "task": "app.workers.tasks.tavily_tasks.tavily_scheduled_task",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        },
    },
)

# Process-local crawler instance initialized once per worker process
_process_crawler = None


def get_process_crawler():
    """Get the process-local crawler initialized by worker startup signal."""
    global _process_crawler
    if _process_crawler is None:
        raise RuntimeError("Crawler not initialized - worker process may not be ready")
    return _process_crawler


@signals.worker_process_init.connect
def init_crawler_for_worker(sender=None, **kwargs):
    """Initialize crawler once per worker process at startup.

    This runs when each Celery worker process starts, not per task.
    All tasks in that process will reuse the same browser instance.
    """
    global _process_crawler
    try:
        import asyncio
        from app.integrations.crawler_client import CrawlerClient

        logger.info("Initializing crawler for worker process")

        # Create new crawler instance for this process
        _process_crawler = CrawlerClient()

        # Initialize asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_process_crawler.initialize())
            logger.info("Crawler successfully initialized for worker process")
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Failed to initialize crawler for worker: {e}", exc_info=True)
        _process_crawler = None


# Import tasks after celery_app is created to avoid circular imports
# This ensures all task decorators are registered with celery_app
try:
    from app.workers.tasks import (
        tavily_tasks, newsapi_tasks, crawl_tasks, trending_tasks,
        digest_tasks, submission_tasks, summary_tasks, evaluation_tasks
    )
except ImportError:
    pass
