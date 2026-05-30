"""Celery app factory and beat schedule."""

import logging
from celery import Celery
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
    worker_concurrency=settings.celery_worker_concurrency,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
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
        "cluster-articles-morning": {
            "task": "tasks.cluster_articles",
            "schedule": crontab(hour=6, minute=0),  # 6:00 AM UTC
        },
        "cluster-articles-evening": {
            "task": "tasks.cluster_articles",
            "schedule": crontab(hour=18, minute=0),  # 6:00 PM UTC
        },
    },
)

# Process-local crawler instance initialized once per worker process
_process_crawler = None


def get_process_crawler():
    """Get a process-local crawler, creating it lazily for crawl tasks only."""
    global _process_crawler
    if _process_crawler is None:
        from app.integrations.crawler_client import CrawlerClient

        logger.info("Creating lazy crawler for worker process")
        _process_crawler = CrawlerClient()
    return _process_crawler


# Import tasks after celery_app is created to avoid circular imports
# This ensures all task decorators are registered with celery_app
try:
    from app.workers.tasks import (
        tavily_tasks, newsapi_tasks, crawl_tasks, trending_tasks,
        digest_tasks, submission_tasks, summary_tasks, evaluation_tasks,
        clustering_tasks, embedding_tasks
    )
except ImportError:
    logger.exception("Failed to import Celery task modules")
    raise
