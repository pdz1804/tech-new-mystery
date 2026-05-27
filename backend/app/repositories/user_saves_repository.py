"""User Saves data repository."""

import asyncio
from pynamodb.exceptions import DoesNotExist

from app.models.user_saves import UserSavesModel
from app.utils.time import now_timestamp


class UserSavesRepository:
    """User saves repository for DynamoDB access."""

    async def get_user_saves(
        self, user_id: str, limit: int = 20, last_key: str | None = None
    ) -> tuple[list[UserSavesModel], str | None]:
        """Get saves for a user with pagination.

        Args:
            user_id: User ID
            limit: Max items per page
            last_key: Pagination cursor from previous response

        Returns:
            Tuple of (items, next_cursor)
        """
        def _query():
            query = UserSavesModel.query(user_id, limit=limit)
            # PynamoDB handles pagination via last_evaluated_key
            items = []
            for item in query:
                items.append(item)
            # Get next cursor from query's last_evaluated_key
            next_cursor = None
            if query.last_evaluated_key:
                next_cursor = str(query.last_evaluated_key)
            return items, next_cursor

        items, next_cursor = await asyncio.to_thread(_query)
        return items, next_cursor

    async def save_article(self, user_id: str, article_id: str) -> UserSavesModel:
        """Save an article for a user."""
        save = UserSavesModel(user_id=user_id, article_id=article_id, saved_at=now_timestamp())
        await asyncio.to_thread(save.save)
        return save

    async def unsave_article(self, user_id: str, article_id: str) -> bool:
        """Remove a saved article."""
        try:
            save = await asyncio.to_thread(UserSavesModel.get, user_id, article_id)
            await asyncio.to_thread(save.delete)
            return True
        except DoesNotExist:
            return False

    async def is_saved(self, user_id: str, article_id: str) -> bool:
        """Check if an article is saved by a user."""
        try:
            await asyncio.to_thread(UserSavesModel.get, user_id, article_id)
            return True
        except DoesNotExist:
            return False
