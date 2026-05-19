"""Comment data repository."""

import asyncio
import uuid
from pynamodb.exceptions import DoesNotExist

from app.models.comment import CommentModel
from app.utils.time import now_timestamp


class CommentRepository:
    """Comment repository for DynamoDB access."""

    async def get_by_id(self, comment_id: str) -> CommentModel | None:
        """Get comment by ID."""
        try:
            return await asyncio.to_thread(CommentModel.get, comment_id)
        except DoesNotExist:
            return None

    async def get_by_article(self, article_id: str, limit: int = 20) -> list[CommentModel]:
        """Get comments for an article."""
        results = await asyncio.to_thread(
            lambda: list(
                CommentModel.article_date_index.query(article_id, limit=limit)
            )
        )
        return results

    async def create(self, comment_data: dict) -> CommentModel:
        """Create a new comment."""
        now = now_timestamp()
        comment = CommentModel(
            comment_id=str(uuid.uuid4()),
            article_id=comment_data["article_id"],
            user_id=comment_data["user_id"],
            content=comment_data["content"],
            created_at=now,
            updated_at=now,
        )
        await asyncio.to_thread(comment.save)
        return comment

    async def delete(self, comment_id: str) -> bool:
        """Delete comment."""
        comment = await self.get_by_id(comment_id)
        if not comment:
            return False
        await asyncio.to_thread(comment.delete)
        return True
