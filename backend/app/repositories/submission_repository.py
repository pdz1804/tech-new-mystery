"""Submission data repository."""

from app.models.submission import SubmissionModel


class SubmissionRepository:
    """Submission repository for DynamoDB access."""

    async def get_by_id(self, submission_id: str) -> SubmissionModel | None:
        """Get submission by ID."""
        pass

    async def get_by_user(self, user_id: str, limit: int = 20) -> list[SubmissionModel]:
        """Get submissions for a user."""
        pass

    async def create(self, submission_data: dict) -> SubmissionModel:
        """Create a new submission."""
        pass

    async def update(self, submission_id: str, **kwargs) -> SubmissionModel:
        """Update submission."""
        pass
