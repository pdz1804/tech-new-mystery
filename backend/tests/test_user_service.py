"""
Comprehensive tests for UserService.
Tests cover: basic cases, hard cases, complex cases, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.user_service import UserService
from app.repositories.user_saves_repository import UserSavesRepository
from app.repositories.user_preferences_repository import UserPreferencesRepository


@pytest.fixture
def mock_user_saves_repo():
    """Mock UserSavesRepository."""
    repo = AsyncMock(spec=UserSavesRepository)
    return repo


@pytest.fixture
def mock_user_prefs_repo():
    """Mock UserPreferencesRepository."""
    repo = AsyncMock(spec=UserPreferencesRepository)
    return repo


@pytest.fixture
def user_service(mock_user_saves_repo, mock_user_prefs_repo):
    """Create UserService with mocked repositories."""
    service = UserService(
        user_saves_repo=mock_user_saves_repo,
        user_prefs_repo=mock_user_prefs_repo,
    )
    # Mock the article repository
    service._article_repo = AsyncMock()
    return service


class TestUserServiceGetPreferences:
    """Tests for getting user preferences."""

    @pytest.mark.asyncio
    async def test_get_preferences_basic_success(self, user_service, mock_user_prefs_repo):
        """BASIC: Successfully get user preferences."""
        mock_prefs = MagicMock()
        mock_prefs.topics = ["technology", "ai"]
        mock_prefs.sources = ["hacker-news", "techcrunch"]
        mock_prefs.notification_enabled = True
        mock_prefs.digest_frequency = "daily"
        mock_prefs.theme = "dark"

        mock_user_prefs_repo.get_by_user_id.return_value = mock_prefs

        result = await user_service.get_user_preferences("user-1")

        assert result["topics"] == ["technology", "ai"]
        assert result["sources"] == ["hacker-news", "techcrunch"]
        assert result["notification_enabled"] is True
        assert result["digest_frequency"] == "daily"
        assert result["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_get_preferences_not_found_returns_defaults(self, user_service, mock_user_prefs_repo):
        """EDGE: Get preferences for user with no preferences (returns defaults)."""
        mock_user_prefs_repo.get_by_user_id.return_value = None

        result = await user_service.get_user_preferences("user-1")

        assert result["topics"] == []
        assert result["sources"] == []
        assert result["notification_enabled"] is False
        assert result["digest_frequency"] == "daily"
        assert result["theme"] == "light"

    @pytest.mark.asyncio
    async def test_get_preferences_with_multiple_topics(self, user_service, mock_user_prefs_repo):
        """HARD: Get preferences with multiple topics and sources."""
        mock_prefs = MagicMock()
        mock_prefs.topics = ["tech", "science", "business", "health"]
        mock_prefs.sources = ["source1", "source2", "source3"]
        mock_prefs.notification_enabled = True
        mock_prefs.digest_frequency = "weekly"
        mock_prefs.theme = "dark"

        mock_user_prefs_repo.get_by_user_id.return_value = mock_prefs

        result = await user_service.get_user_preferences("user-1")

        assert len(result["topics"]) == 4
        assert len(result["sources"]) == 3

    @pytest.mark.asyncio
    async def test_get_preferences_response_structure(self, user_service, mock_user_prefs_repo):
        """COMPLEX: Verify preferences response has all required fields."""
        mock_prefs = MagicMock()
        mock_prefs.topics = []
        mock_prefs.sources = []
        mock_prefs.notification_enabled = False
        mock_prefs.digest_frequency = "daily"
        mock_prefs.theme = "light"

        mock_user_prefs_repo.get_by_user_id.return_value = mock_prefs

        result = await user_service.get_user_preferences("user-1")

        assert "topics" in result
        assert "sources" in result
        assert "notification_enabled" in result
        assert "digest_frequency" in result
        assert "theme" in result
        assert len(result) == 5


class TestUserServiceUpdatePreferences:
    """Tests for updating user preferences."""

    @pytest.mark.asyncio
    async def test_update_preferences_basic_success(self, user_service, mock_user_prefs_repo):
        """BASIC: Successfully update user preferences."""
        mock_prefs = MagicMock()
        mock_prefs.topics = ["technology"]
        mock_prefs.sources = ["hacker-news"]
        mock_prefs.notification_enabled = True
        mock_prefs.digest_frequency = "daily"
        mock_prefs.theme = "dark"

        mock_user_prefs_repo.update.return_value = mock_prefs

        result = await user_service.update_user_preferences(
            "user-1",
            {
                "topics": ["technology"],
                "sources": ["hacker-news"],
                "notification_enabled": True,
                "digest_frequency": "daily",
                "theme": "dark",
            },
        )

        assert result["topics"] == ["technology"]
        assert result["theme"] == "dark"
        mock_user_prefs_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_preferences_partial_update(self, user_service, mock_user_prefs_repo):
        """HARD: Update only specific preferences."""
        mock_prefs = MagicMock()
        mock_prefs.topics = ["technology", "ai"]
        mock_prefs.sources = []
        mock_prefs.notification_enabled = False
        mock_prefs.digest_frequency = "weekly"
        mock_prefs.theme = "dark"

        mock_user_prefs_repo.update.return_value = mock_prefs

        result = await user_service.update_user_preferences(
            "user-1",
            {"theme": "dark", "digest_frequency": "weekly"},
        )

        assert result["theme"] == "dark"
        assert result["digest_frequency"] == "weekly"

    @pytest.mark.asyncio
    async def test_update_preferences_empty_preferences(self, user_service, mock_user_prefs_repo):
        """COMPLEX: Update to empty lists."""
        mock_prefs = MagicMock()
        mock_prefs.topics = []
        mock_prefs.sources = []
        mock_prefs.notification_enabled = False
        mock_prefs.digest_frequency = "daily"
        mock_prefs.theme = "light"

        mock_user_prefs_repo.update.return_value = mock_prefs

        result = await user_service.update_user_preferences(
            "user-1",
            {"topics": [], "sources": []},
        )

        assert result["topics"] == []
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_update_preferences_response_structure(self, user_service, mock_user_prefs_repo):
        """COMPLEX: Verify update response has all required fields."""
        mock_prefs = MagicMock()
        mock_prefs.topics = ["tech"]
        mock_prefs.sources = ["hn"]
        mock_prefs.notification_enabled = True
        mock_prefs.digest_frequency = "daily"
        mock_prefs.theme = "dark"

        mock_user_prefs_repo.update.return_value = mock_prefs

        result = await user_service.update_user_preferences("user-1", {"theme": "dark"})

        assert "topics" in result
        assert "sources" in result
        assert "notification_enabled" in result
        assert "digest_frequency" in result
        assert "theme" in result
        assert len(result) == 5


class TestUserServiceGetSavedArticles:
    """Tests for getting saved articles."""

    @pytest.mark.asyncio
    async def test_get_saved_articles_basic_success(self, user_service, mock_user_saves_repo):
        """BASIC: Successfully get user's saved articles."""
        mock_save1 = MagicMock()
        mock_save1.article_id = "art-1"
        mock_save1.saved_at = 1234567890

        mock_save2 = MagicMock()
        mock_save2.article_id = "art-2"
        mock_save2.saved_at = 1234567895

        mock_user_saves_repo.get_user_saves.return_value = [mock_save1, mock_save2]

        # Mock articles
        mock_article1 = MagicMock()
        mock_article1.article_id = "art-1"
        mock_article1.title = "Article 1"
        mock_article1.slug = "article-1"
        mock_article1.summary = "Summary 1"
        mock_article1.category = "Tech"
        mock_article1.tags = ["tech"]
        mock_article1.original_url = "http://example.com/1"
        mock_article1.source_id = "source-1"
        mock_article1.view_count = 10
        mock_article1.is_published = True
        mock_article1.published_at = 1234567800
        mock_article1.created_at = 1234567800

        mock_article2 = MagicMock()
        mock_article2.article_id = "art-2"
        mock_article2.title = "Article 2"
        mock_article2.slug = "article-2"
        mock_article2.summary = "Summary 2"
        mock_article2.category = "Science"
        mock_article2.tags = ["science"]
        mock_article2.original_url = "http://example.com/2"
        mock_article2.source_id = "source-2"
        mock_article2.view_count = 20
        mock_article2.is_published = True
        mock_article2.published_at = 1234567801
        mock_article2.created_at = 1234567801

        user_service._article_repo.get_by_id.side_effect = [mock_article1, mock_article2]

        result = await user_service.get_saved_articles("user-1")

        assert len(result) == 2
        assert result[0]["article_id"] == "art-1"
        assert result[0]["title"] == "Article 1"
        assert result[1]["article_id"] == "art-2"
        assert result[1]["title"] == "Article 2"

    @pytest.mark.asyncio
    async def test_get_saved_articles_empty(self, user_service, mock_user_saves_repo):
        """EDGE: Get saved articles when none exist."""
        mock_user_saves_repo.get_user_saves.return_value = []

        result = await user_service.get_saved_articles("user-1")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_saved_articles_with_limit(self, user_service, mock_user_saves_repo):
        """HARD: Get saved articles with limit."""
        mock_saves = [
            MagicMock(article_id=f"art-{i}", saved_at=1234567890 + i)
            for i in range(5)
        ]

        mock_user_saves_repo.get_user_saves.return_value = mock_saves[:10]

        # Mock articles
        mock_articles = []
        for i in range(5):
            article = MagicMock()
            article.article_id = f"art-{i}"
            article.title = f"Article {i}"
            article.slug = f"article-{i}"
            article.summary = f"Summary {i}"
            article.category = "Tech"
            article.tags = ["tech"]
            article.original_url = f"http://example.com/{i}"
            article.source_id = "source-1"
            article.view_count = i * 10
            article.is_published = True
            article.published_at = 1234567800 + i
            article.created_at = 1234567800 + i
            mock_articles.append(article)

        user_service._article_repo.get_by_id.side_effect = mock_articles

        result = await user_service.get_saved_articles("user-1", limit=10)

        assert len(result) == 5
        mock_user_saves_repo.get_user_saves.assert_called_once_with("user-1", limit=10)

    @pytest.mark.asyncio
    async def test_get_saved_articles_response_structure(self, user_service, mock_user_saves_repo):
        """COMPLEX: Verify saved articles response structure."""
        mock_save = MagicMock()
        mock_save.article_id = "art-1"
        mock_save.saved_at = 1234567890

        mock_user_saves_repo.get_user_saves.return_value = [mock_save]

        # Mock article with full details
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = "Article 1"
        mock_article.slug = "article-1"
        mock_article.summary = "Summary 1"
        mock_article.category = "Tech"
        mock_article.tags = ["tech"]
        mock_article.original_url = "http://example.com/1"
        mock_article.source_id = "source-1"
        mock_article.view_count = 10
        mock_article.is_published = True
        mock_article.published_at = 1234567800
        mock_article.created_at = 1234567800

        user_service._article_repo.get_by_id.return_value = mock_article

        result = await user_service.get_saved_articles("user-1")

        assert len(result) == 1
        saved = result[0]
        assert "article_id" in saved
        assert "title" in saved
        assert "slug" in saved
        assert "summary" in saved
        assert "category" in saved
        assert saved["article_id"] == "art-1"
        assert saved["title"] == "Article 1"


class TestUserServiceSaveArticle:
    """Tests for saving articles."""

    @pytest.mark.asyncio
    async def test_save_article_basic_success(self, user_service, mock_user_saves_repo):
        """BASIC: Successfully save an article."""
        mock_save = MagicMock()
        mock_save.article_id = "art-1"
        mock_save.saved_at = 1234567890

        mock_user_saves_repo.save_article.return_value = mock_save

        result = await user_service.save_article("user-1", "art-1")

        assert result["article_id"] == "art-1"
        assert result["saved_at"] == 1234567890
        mock_user_saves_repo.save_article.assert_called_once_with("user-1", "art-1")

    @pytest.mark.asyncio
    async def test_save_article_idempotent(self, user_service, mock_user_saves_repo):
        """HARD: Save same article twice."""
        mock_save = MagicMock()
        mock_save.article_id = "art-1"
        mock_save.saved_at = 1234567890

        mock_user_saves_repo.save_article.return_value = mock_save

        result1 = await user_service.save_article("user-1", "art-1")
        result2 = await user_service.save_article("user-1", "art-1")

        assert result1["article_id"] == result2["article_id"]
        assert mock_user_saves_repo.save_article.call_count == 2

    @pytest.mark.asyncio
    async def test_save_article_multiple_articles(self, user_service, mock_user_saves_repo):
        """COMPLEX: Save multiple different articles."""
        def mock_save_article(user_id, article_id):
            mock_save = MagicMock()
            mock_save.article_id = article_id
            mock_save.saved_at = 1234567890
            return mock_save

        mock_user_saves_repo.save_article.side_effect = mock_save_article

        result1 = await user_service.save_article("user-1", "art-1")
        result2 = await user_service.save_article("user-1", "art-2")

        assert result1["article_id"] == "art-1"
        assert result2["article_id"] == "art-2"

    @pytest.mark.asyncio
    async def test_save_article_response_structure(self, user_service, mock_user_saves_repo):
        """COMPLEX: Verify save response has required fields."""
        mock_save = MagicMock()
        mock_save.article_id = "art-1"
        mock_save.saved_at = 1234567890

        mock_user_saves_repo.save_article.return_value = mock_save

        result = await user_service.save_article("user-1", "art-1")

        assert "article_id" in result
        assert "saved_at" in result
        assert len(result) == 2


class TestUserServiceUnsaveArticle:
    """Tests for unsaving articles."""

    @pytest.mark.asyncio
    async def test_unsave_article_basic_success(self, user_service, mock_user_saves_repo):
        """BASIC: Successfully unsave an article."""
        mock_user_saves_repo.unsave_article.return_value = True

        result = await user_service.unsave_article("user-1", "art-1")

        assert result is True
        mock_user_saves_repo.unsave_article.assert_called_once_with("user-1", "art-1")

    @pytest.mark.asyncio
    async def test_unsave_article_not_saved(self, user_service, mock_user_saves_repo):
        """EDGE: Unsave article that was never saved."""
        mock_user_saves_repo.unsave_article.return_value = False

        result = await user_service.unsave_article("user-1", "art-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_unsave_article_twice(self, user_service, mock_user_saves_repo):
        """HARD: Unsave same article twice."""
        mock_user_saves_repo.unsave_article.side_effect = [True, False]

        result1 = await user_service.unsave_article("user-1", "art-1")
        result2 = await user_service.unsave_article("user-1", "art-1")

        assert result1 is True
        assert result2 is False

    @pytest.mark.asyncio
    async def test_unsave_article_multiple_articles(self, user_service, mock_user_saves_repo):
        """COMPLEX: Unsave multiple articles."""
        mock_user_saves_repo.unsave_article.side_effect = [True, True, False]

        result1 = await user_service.unsave_article("user-1", "art-1")
        result2 = await user_service.unsave_article("user-1", "art-2")
        result3 = await user_service.unsave_article("user-1", "art-3")

        assert result1 is True
        assert result2 is True
        assert result3 is False

    @pytest.mark.asyncio
    async def test_unsave_article_return_type(self, user_service, mock_user_saves_repo):
        """COMPLEX: Verify unsave returns boolean."""
        mock_user_saves_repo.unsave_article.return_value = True

        result = await user_service.unsave_article("user-1", "art-1")

        assert isinstance(result, bool)
        assert result is True
