"""Celery app factory and beat schedule."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

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
