"""
Tests for RBAC and Engagement Features (Likes, Saves, View Counts).
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories.user_repository import UserRepository
from app.repositories.article_repository import ArticleRepository
from app.repositories.user_likes_repository import UserLikesRepository
from app.repositories.user_saves_repository import UserSavesRepository
from app.services.article_service import ArticleService
from app.core.exceptions import ArticleNotFoundError


# ============ User Model & Repository Tests ============

class TestUserRepository:
    """Tests for UserRepository role-related methods."""

    @pytest.fixture
    def mock_user_repo(self):
        """Create a UserRepository with mocked DynamoDB."""
        return UserRepository()

    @pytest.mark.asyncio
    async def test_is_admin_returns_true_for_admin_user(self):
        """Test that is_admin returns True for admin users."""
        repo = UserRepository()

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_user = MagicMock()
            mock_user.is_admin = True
            mock_to_thread.return_value = mock_user

            result = await repo.is_admin("admin-user-id")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_returns_false_for_non_admin_user(self):
        """Test that is_admin returns False for non-admin users."""
        repo = UserRepository()

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_user = MagicMock()
            mock_user.is_admin = False
            mock_to_thread.return_value = mock_user

            result = await repo.is_admin("regular-user-id")
            assert result is False

    @pytest.mark.asyncio
    async def test_is_active_returns_true_for_active_user(self):
        """Test that is_active returns True for active users."""
        repo = UserRepository()

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_user = MagicMock()
            mock_user.is_active = True
            mock_to_thread.return_value = mock_user

            result = await repo.is_active("active-user-id")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_active_returns_false_for_inactive_user(self):
        """Test that is_active returns False for inactive users."""
        repo = UserRepository()

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_user = MagicMock()
            mock_user.is_active = False
            mock_to_thread.return_value = mock_user

            result = await repo.is_active("inactive-user-id")
            assert result is False


# ============ Like Feature Tests ============

class TestUserLikesRepository:
    """Tests for UserLikesRepository."""

    @pytest.fixture
    def mock_likes_repo(self):
        """Create a UserLikesRepository."""
        return UserLikesRepository()

    @pytest.mark.asyncio
    async def test_like_article_creates_like_record(self, mock_likes_repo):
        """Test that like_article creates a like record."""
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_like = MagicMock()
            mock_to_thread.return_value = None  # save() doesn't return anything

            result = await mock_likes_repo.like_article("user-1", "article-1")
            assert result is not None

    @pytest.mark.asyncio
    async def test_unlike_article_removes_like(self, mock_likes_repo):
        """Test that unlike_article removes a like."""
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_like = MagicMock()
            mock_to_thread.return_value = mock_like

            result = await mock_likes_repo.unlike_article("user-1", "article-1")
            assert result is True

    @pytest.mark.asyncio
    async def test_unlike_article_returns_false_if_not_found(self, mock_likes_repo):
        """Test that unlike_article returns False if like doesn't exist."""
        from pynamodb.exceptions import DoesNotExist

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = DoesNotExist()

            result = await mock_likes_repo.unlike_article("user-1", "article-1")
            assert result is False

    @pytest.mark.asyncio
    async def test_is_liked_returns_true_if_liked(self, mock_likes_repo):
        """Test that is_liked returns True if article is liked."""
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_like = MagicMock()
            mock_to_thread.return_value = mock_like

            result = await mock_likes_repo.is_liked("user-1", "article-1")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_liked_returns_false_if_not_liked(self, mock_likes_repo):
        """Test that is_liked returns False if article is not liked."""
        from pynamodb.exceptions import DoesNotExist

        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = DoesNotExist()

            result = await mock_likes_repo.is_liked("user-1", "article-1")
            assert result is False


class TestArticleServiceLikes:
    """Tests for ArticleService like operations."""

    @pytest.fixture
    def setup(self):
        """Setup for tests."""
        mock_article_repo = AsyncMock(spec=ArticleRepository)
        service = ArticleService(article_repo=mock_article_repo)
        return {
            "service": service,
            "article_repo": mock_article_repo,
        }

    @pytest.mark.asyncio
    async def test_like_article_success(self, setup):
        """Test successfully liking an article."""
        service = setup["service"]
        article_repo = setup["article_repo"]

        mock_article = MagicMock()
        mock_article.article_id = "article-1"
        mock_article.like_count = 5

        article_repo.get_by_id.return_value = mock_article
        service._user_likes_repo = AsyncMock()
        service._user_likes_repo.is_liked.return_value = False

        result = await service.like_article("user-1", "article-1")

        assert result["success"] is True
        assert "Article liked" in result["message"]
        article_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_like_article_already_liked_raises_error(self, setup):
        """Test that liking an already-liked article raises error."""
        service = setup["service"]
        article_repo = setup["article_repo"]

        mock_article = MagicMock()
        mock_article.article_id = "article-1"

        article_repo.get_by_id.return_value = mock_article
        service._user_likes_repo = AsyncMock()
        service._user_likes_repo.is_liked.return_value = True

        with pytest.raises(ValueError, match="already liked"):
            await service.like_article("user-1", "article-1")

    @pytest.mark.asyncio
    async def test_unlike_article_success(self, setup):
        """Test successfully unliking an article."""
        service = setup["service"]
        article_repo = setup["article_repo"]

        mock_article = MagicMock()
        mock_article.article_id = "article-1"
        mock_article.like_count = 5

        article_repo.get_by_id.return_value = mock_article
        service._user_likes_repo = AsyncMock()
        service._user_likes_repo.is_liked.return_value = True

        result = await service.unlike_article("user-1", "article-1")

        assert result["success"] is True
        assert "unliked" in result["message"]
        article_repo.update.assert_called_once_with("article-1", like_count=4)

    @pytest.mark.asyncio
    async def test_unlike_article_not_liked_raises_error(self, setup):
        """Test that unliking a non-liked article raises error."""
        service = setup["service"]
        article_repo = setup["article_repo"]

        mock_article = MagicMock()
        mock_article.article_id = "article-1"

        article_repo.get_by_id.return_value = mock_article
        service._user_likes_repo = AsyncMock()
        service._user_likes_repo.is_liked.return_value = False

        with pytest.raises(ValueError, match="not liked"):
            await service.unlike_article("user-1", "article-1")

    @pytest.mark.asyncio
    async def test_get_like_count_returns_correct_count(self, setup):
        """Test getting like count for an article."""
        service = setup["service"]
        article_repo = setup["article_repo"]

        mock_article = MagicMock()
        mock_article.article_id = "article-1"
        mock_article.like_count = 42

        article_repo.get_by_id.return_value = mock_article

        result = await service.get_like_count("article-1")

        assert result["article_id"] == "article-1"
        assert result["like_count"] == 42


# ============ Save Feature Tests ============

class TestUserSavesRepository:
    """Tests for UserSavesRepository."""

    @pytest.fixture
    def saves_repo(self):
        """Create a UserSavesRepository."""
        return UserSavesRepository()

    @pytest.mark.asyncio
    async def test_save_article_creates_record(self, saves_repo):
        """Test that save_article creates a save record."""
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_save = MagicMock()
            mock_to_thread.return_value = None

            result = await saves_repo.save_article("user-1", "article-1")
            assert result is not None

    @pytest.mark.asyncio
    async def test_unsave_article_removes_save(self, saves_repo):
        """Test that unsave_article removes a save."""
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_save = MagicMock()
            mock_to_thread.return_value = mock_save

            result = await saves_repo.unsave_article("user-1", "article-1")
            assert result is True

    @pytest.mark.asyncio
    async def test_get_user_saves_returns_saves(self, saves_repo):
        """Test that get_user_saves returns user's saves."""
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_save1 = MagicMock()
            mock_save1.article_id = "article-1"
            mock_save2 = MagicMock()
            mock_save2.article_id = "article-2"
            mock_to_thread.return_value = [mock_save1, mock_save2]

            result = await saves_repo.get_user_saves("user-1")
            assert len(result) == 2


# ============ View Count Feature Tests ============

class TestArticleServiceViewCount:
    """Tests for ArticleService view count operations."""

    @pytest.fixture
    def setup(self):
        """Setup for tests."""
        mock_article_repo = AsyncMock(spec=ArticleRepository)
        service = ArticleService(article_repo=mock_article_repo)
        return {
            "service": service,
            "article_repo": mock_article_repo,
        }

    @pytest.mark.asyncio
    async def test_increment_view_count_success(self, setup):
        """Test successfully incrementing view count."""
        service = setup["service"]
        article_repo = setup["article_repo"]

        mock_article = MagicMock()
        mock_article.article_id = "article-1"
        mock_article.view_count = 10

        article_repo.get_by_id.return_value = mock_article

        result = await service.increment_view_count("article-1")

        assert result["article_id"] == "article-1"
        assert result["view_count"] == 11
        article_repo.update.assert_called_once_with("article-1", view_count=11)

    @pytest.mark.asyncio
    async def test_increment_view_count_article_not_found(self, setup):
        """Test that incrementing view count for non-existent article raises error."""
        service = setup["service"]
        article_repo = setup["article_repo"]

        article_repo.get_by_id.return_value = None

        with pytest.raises(ArticleNotFoundError):
            await service.increment_view_count("nonexistent-id")


# ============ Integration Tests ============

class TestEngagementFeaturesIntegration:
    """Integration tests for engagement features."""

    @pytest.mark.asyncio
    async def test_article_with_likes_and_views(self):
        """Test article tracking both likes and views."""
        mock_article_repo = AsyncMock(spec=ArticleRepository)
        service = ArticleService(article_repo=mock_article_repo)

        mock_article = MagicMock()
        mock_article.article_id = "article-1"
        mock_article.like_count = 0
        mock_article.view_count = 0

        mock_article_repo.get_by_id.return_value = mock_article

        # Like the article
        service._user_likes_repo = AsyncMock()
        service._user_likes_repo.is_liked.return_value = False

        like_result = await service.like_article("user-1", "article-1")
        assert like_result["success"] is True

        # Increment view count
        view_result = await service.increment_view_count("article-1")
        assert view_result["view_count"] == 1
