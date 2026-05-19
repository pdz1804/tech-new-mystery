"""User Likes data repository."""

import asyncio
from pynamodb.exceptions import DoesNotExist

from app.models.user_likes import UserLikesModel
from app.utils.time import now_timestamp


class UserLikesRepository:
    """User likes repository for DynamoDB access."""

    async def get_user_likes(self, user_id: str, limit: int = 100) -> list[UserLikesModel]:
        """Get all likes for a user."""
        results = await asyncio.to_thread(
            lambda: list(UserLikesModel.query(user_id, limit=limit))
        )
        return results

    async def like_article(self, user_id: str, article_id: str) -> UserLikesModel:
        """Like an article for a user."""
        like = UserLikesModel(user_id=user_id, article_id=article_id, liked_at=now_timestamp())
        await asyncio.to_thread(like.save)
        return like

    async def unlike_article(self, user_id: str, article_id: str) -> bool:
        """Remove a like from an article."""
        try:
            like = await asyncio.to_thread(UserLikesModel.get, user_id, article_id)
            await asyncio.to_thread(like.delete)
            return True
        except DoesNotExist:
            return False

    async def is_liked(self, user_id: str, article_id: str) -> bool:
        """Check if an article is liked by a user."""
        try:
            await asyncio.to_thread(UserLikesModel.get, user_id, article_id)
            return True
        except DoesNotExist:
            return False

    async def get_like_count(self, article_id: str) -> int:
        """Get the count of likes for an article."""
        # Scan all likes for the article (this is a limitation of DynamoDB design)
        # In production, this count should be cached or maintained separately
        results = await asyncio.to_thread(
            lambda: list(UserLikesModel.scan(
                UserLikesModel.article_id == article_id
            ))
        )
        return len(results)
