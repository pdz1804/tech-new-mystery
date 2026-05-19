"""Tests for Celery Beat scheduler configuration."""

import pytest
from app.workers.celery_app import celery_app


class TestCeleryScheduler:
    """Tests for Celery scheduler configuration."""

    def test_beat_schedule_configured(self):
        """Test that beat schedule is configured."""
        assert celery_app.conf.beat_schedule is not None
        assert len(celery_app.conf.beat_schedule) > 0

    def test_daily_crawl_task_configured(self):
        """Test that daily crawl task is scheduled."""
        schedule = celery_app.conf.beat_schedule
        assert "crawl-news-daily" in schedule

        crawl_task = schedule["crawl-news-daily"]
        assert crawl_task["task"] == "app.workers.tasks.crawl_tasks.daily_crawl_task"
        assert crawl_task["schedule"] is not None

    def test_recalculate_trending_task_configured(self):
        """Test that trending recalculation is scheduled."""
        schedule = celery_app.conf.beat_schedule
        assert "recalculate-trending" in schedule

        trending_task = schedule["recalculate-trending"]
        assert trending_task["task"] == "app.workers.tasks.trending_tasks.recalculate_trending_task"
        assert trending_task["schedule"] is not None

    def test_celery_timezone_configured(self):
        """Test that timezone is configured."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_serializer_configured(self):
        """Test that serializer is configured."""
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        assert celery_app.conf.result_serializer == "json"

    def test_daily_crawl_schedule_time(self):
        """Test that daily crawl is scheduled for 2 AM UTC."""
        from celery.schedules import crontab

        schedule = celery_app.conf.beat_schedule
        crawl_schedule = schedule["crawl-news-daily"]["schedule"]

        # Verify it's a crontab object
        assert isinstance(crawl_schedule, crontab)

        # Verify hour and minute
        assert crawl_schedule.hour == {2}
        assert crawl_schedule.minute == {0}

    def test_trending_schedule_frequency(self):
        """Test that trending is recalculated every 30 minutes."""
        from celery.schedules import crontab

        schedule = celery_app.conf.beat_schedule
        trending_schedule = schedule["recalculate-trending"]["schedule"]

        # Verify it's a crontab object
        assert isinstance(trending_schedule, crontab)

        # Verify minute pattern
        expected_minutes = set(range(0, 60, 30))  # 0 and 30
        assert trending_schedule.minute == expected_minutes

    def test_tasks_module_imports(self):
        """Test that task modules can be imported."""
        try:
            from app.workers.tasks import crawl_tasks
            from app.workers.tasks import trending_tasks

            assert hasattr(crawl_tasks, "daily_crawl_task")
            assert hasattr(trending_tasks, "recalculate_trending_task")
        except ImportError as e:
            pytest.fail(f"Failed to import task modules: {e}")
