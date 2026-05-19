"""User submission tasks."""

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def process_submission_task(self, submission_id: str) -> dict:
    """Process a user-submitted article."""
    try:
        raise NotImplementedError
    except Exception as exc:
        raise self.retry(exc=exc)
