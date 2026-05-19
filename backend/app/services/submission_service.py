"""Submission business logic service."""

from app.repositories.submission_repository import SubmissionRepository


class SubmissionService:
    """Submission service for business logic."""

    def __init__(self, submission_repo: SubmissionRepository) -> None:
        """Initialize service."""
        self._submission_repo = submission_repo

    async def submit_article(self, user_id: str, url: str) -> dict:
        """Submit an article URL for processing."""
        raise NotImplementedError

    async def get_user_submissions(self, user_id: str) -> list[dict]:
        """Get user's submissions."""
        raise NotImplementedError
