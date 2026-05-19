"""User data repository."""

import asyncio
from pynamodb.exceptions import DoesNotExist

from app.models.user import UserModel


class UserRepository:
    """User repository for DynamoDB access."""

    async def get_by_id(self, user_id: str) -> UserModel | None:
        """Get user by ID."""
        try:
            return await asyncio.to_thread(UserModel.get, user_id)
        except DoesNotExist:
            return None

    async def get_by_username(self, username: str) -> UserModel | None:
        """Get user by username."""
        results = await asyncio.to_thread(
            lambda: list(UserModel.username_index.query(username, limit=1))
        )
        return results[0] if results else None

    async def create(
        self,
        user_id: str,
        username: str,
        password_hash: str,
        email: str,
    ) -> UserModel:
        """Create a new user."""
        from app.utils.time import now_timestamp

        user = UserModel(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            email=email,
            is_admin=False,
            is_active=True,
            created_at=now_timestamp(),
            updated_at=now_timestamp(),
        )
        await asyncio.to_thread(user.save)
        return user

    async def update(self, user_id: str, **kwargs) -> UserModel:
        """Update user."""
        from app.utils.time import now_timestamp

        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = now_timestamp()
        await asyncio.to_thread(user.save)
        return user

    async def is_admin(self, user_id: str) -> bool:
        """Check if user is an admin."""
        user = await self.get_by_id(user_id)
        return user.is_admin if user else False

    async def is_active(self, user_id: str) -> bool:
        """Check if user is active."""
        user = await self.get_by_id(user_id)
        return user.is_active if user else False
