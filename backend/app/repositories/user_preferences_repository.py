"""User Preferences data repository."""

import asyncio
from pynamodb.exceptions import DoesNotExist

from app.models.user_preferences import UserPreferencesModel
from app.utils.time import now_timestamp


class UserPreferencesRepository:
    """User preferences repository for DynamoDB access."""

    async def get_by_user_id(self, user_id: str) -> UserPreferencesModel | None:
        """Get preferences for a user."""
        try:
            return await asyncio.to_thread(UserPreferencesModel.get, user_id)
        except DoesNotExist:
            return None

    async def create(self, user_id: str, preferences_data: dict) -> UserPreferencesModel:
        """Create user preferences."""
        prefs = UserPreferencesModel(
            user_id=user_id,
            topics=preferences_data.get("topics", []),
            sources=preferences_data.get("sources", []),
            notification_enabled=preferences_data.get("notification_enabled", False),
            digest_frequency=preferences_data.get("digest_frequency", "daily"),
            theme=preferences_data.get("theme", "light"),
            created_at=now_timestamp(),
            updated_at=now_timestamp(),
        )
        await asyncio.to_thread(prefs.save)
        return prefs

    async def update(self, user_id: str, **kwargs) -> UserPreferencesModel:
        """Update user preferences."""
        prefs = await self.get_by_user_id(user_id)
        if prefs is None:
            # Create if doesn't exist
            return await self.create(user_id, kwargs)

        for key, value in kwargs.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)

        prefs.updated_at = now_timestamp()
        await asyncio.to_thread(prefs.save)
        return prefs
