"""User business logic service."""

from app.core.exceptions import NotFoundError
from app.repositories.user_saves_repository import UserSavesRepository
from app.repositories.user_preferences_repository import UserPreferencesRepository
from app.repositories.article_repository import ArticleRepository
from app.utils.time import timestamp_to_datetime


class UserService:
    """User service for business logic."""

    def __init__(
        self,
        user_saves_repo: UserSavesRepository,
        user_prefs_repo: UserPreferencesRepository,
    ) -> None:
        """Initialize service."""
        self._user_saves_repo = user_saves_repo
        self._user_prefs_repo = user_prefs_repo
        self._article_repo = ArticleRepository()

    async def get_user_preferences(self, user_id: str) -> dict:
        """Get user preferences."""
        prefs = await self._user_prefs_repo.get_by_user_id(user_id)
        if not prefs:
            # Return defaults if not yet created
            return {
                "topics": [],
                "sources": [],
                "notification_enabled": False,
                "digest_frequency": "daily",
                "theme": "light",
            }

        return {
            "topics": prefs.topics,
            "sources": prefs.sources,
            "notification_enabled": prefs.notification_enabled,
            "digest_frequency": prefs.digest_frequency,
            "theme": prefs.theme,
        }

    async def update_user_preferences(self, user_id: str, preferences: dict) -> dict:
        """Update user preferences."""
        prefs = await self._user_prefs_repo.update(user_id, **preferences)

        return {
            "topics": prefs.topics,
            "sources": prefs.sources,
            "notification_enabled": prefs.notification_enabled,
            "digest_frequency": prefs.digest_frequency,
            "theme": prefs.theme,
        }

    async def get_saved_articles(self, user_id: str, limit: int = 20) -> list[dict]:
        """Get user's saved articles with full article details."""
        saves = await self._user_saves_repo.get_user_saves(user_id, limit=limit)
        articles = []

        for save in saves:
            article = await self._article_repo.get_by_id(save.article_id)
            if article:
                articles.append({
                    "article_id": article.article_id,
                    "title": article.title,
                    "slug": article.slug,
                    "summary": article.summary,
                    "category": article.category,
                    "tags": article.tags,
                    "original_url": article.original_url,
                    "source_id": article.source_id,
                    "view_count": article.view_count,
                    "is_published": article.is_published,
                    "published_at": timestamp_to_datetime(article.published_at) if article.published_at else None,
                    "created_at": timestamp_to_datetime(article.created_at) if article.created_at else None,
                })

        return articles

    async def save_article(self, user_id: str, article_id: str) -> dict:
        """Save an article for a user."""
        save = await self._user_saves_repo.save_article(user_id, article_id)
        return {
            "article_id": save.article_id,
            "saved_at": save.saved_at,
        }

    async def unsave_article(self, user_id: str, article_id: str) -> bool:
        """Unsave an article."""
        return await self._user_saves_repo.unsave_article(user_id, article_id)
