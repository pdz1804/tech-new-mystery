"""
Comprehensive tests for CommentService.
Tests cover: basic cases, hard cases, complex cases, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.comment_service import CommentService
from app.repositories.comment_repository import CommentRepository


@pytest.fixture
def mock_comment_repo():
    """Mock CommentRepository."""
    repo = AsyncMock(spec=CommentRepository)
    return repo


@pytest.fixture
def comment_service(mock_comment_repo):
    """Create CommentService with mocked repository."""
    return CommentService(comment_repo=mock_comment_repo)


class TestCommentServiceGetArticleComments:
    """Tests for getting comments by article."""

    @pytest.mark.asyncio
    async def test_get_article_comments_basic_success(self, comment_service, mock_comment_repo):
        """BASIC: Successfully get comments for an article."""
        mock_comment1 = MagicMock()
        mock_comment1.comment_id = "comm-1"
        mock_comment1.user_id = "user-1"
        mock_comment1.content = "Great article!"
        mock_comment1.created_at = 1234567890

        mock_comment2 = MagicMock()
        mock_comment2.comment_id = "comm-2"
        mock_comment2.user_id = "user-2"
        mock_comment2.content = "Thanks for sharing"
        mock_comment2.created_at = 1234567895

        mock_comment_repo.get_by_article.return_value = [mock_comment1, mock_comment2]

        result = await comment_service.get_article_comments("art-1", limit=20)

        assert len(result) == 2
        assert result[0]["comment_id"] == "comm-1"
        assert result[0]["content"] == "Great article!"
        assert result[1]["user_id"] == "user-2"

    @pytest.mark.asyncio
    async def test_get_article_comments_empty(self, comment_service, mock_comment_repo):
        """EDGE: Get comments when none exist for article."""
        mock_comment_repo.get_by_article.return_value = []

        result = await comment_service.get_article_comments("art-1")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_article_comments_with_limit(self, comment_service, mock_comment_repo):
        """HARD: Get comments with limit parameter."""
        mock_comments = [
            MagicMock(
                comment_id=f"comm-{i}",
                user_id=f"user-{i}",
                content=f"Comment {i}",
                created_at=1234567890 + i,
            )
            for i in range(5)
        ]

        mock_comment_repo.get_by_article.return_value = mock_comments[:3]

        result = await comment_service.get_article_comments("art-1", limit=3)

        assert len(result) == 3
        mock_comment_repo.get_by_article.assert_called_once_with("art-1", limit=3)

    @pytest.mark.asyncio
    async def test_get_article_comments_response_structure(self, comment_service, mock_comment_repo):
        """COMPLEX: Verify response structure has required fields."""
        mock_comment = MagicMock()
        mock_comment.comment_id = "comm-1"
        mock_comment.user_id = "user-1"
        mock_comment.content = "Test comment"
        mock_comment.created_at = 1234567890

        mock_comment_repo.get_by_article.return_value = [mock_comment]

        result = await comment_service.get_article_comments("art-1")

        assert len(result) == 1
        comment_dict = result[0]
        assert "comment_id" in comment_dict
        assert "user_id" in comment_dict
        assert "content" in comment_dict
        assert "created_at" in comment_dict
        assert len(comment_dict) == 4


class TestCommentServiceCreateComment:
    """Tests for creating comments."""

    @pytest.mark.asyncio
    async def test_create_comment_basic_success(self, comment_service, mock_comment_repo):
        """BASIC: Successfully create a comment."""
        mock_comment = MagicMock()
        mock_comment.comment_id = "comm-1"
        mock_comment.user_id = "user-1"
        mock_comment.content = "Great article!"
        mock_comment.created_at = 1234567890

        mock_comment_repo.create.return_value = mock_comment

        result = await comment_service.create_comment("art-1", "user-1", "Great article!")

        assert result["comment_id"] == "comm-1"
        assert result["user_id"] == "user-1"
        assert result["content"] == "Great article!"
        mock_comment_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_comment_with_long_content(self, comment_service, mock_comment_repo):
        """HARD: Create comment with very long content."""
        long_content = "A" * 5000
        mock_comment = MagicMock()
        mock_comment.comment_id = "comm-1"
        mock_comment.user_id = "user-1"
        mock_comment.content = long_content
        mock_comment.created_at = 1234567890

        mock_comment_repo.create.return_value = mock_comment

        result = await comment_service.create_comment("art-1", "user-1", long_content)

        assert result["content"] == long_content
        assert len(result["content"]) == 5000

    @pytest.mark.asyncio
    async def test_create_comment_with_special_characters(self, comment_service, mock_comment_repo):
        """COMPLEX: Create comment with special characters."""
        content = "Check this: @user #hashtag & <script>alert(1)</script> 😀"
        mock_comment = MagicMock()
        mock_comment.comment_id = "comm-1"
        mock_comment.user_id = "user-1"
        mock_comment.content = content
        mock_comment.created_at = 1234567890

        mock_comment_repo.create.return_value = mock_comment

        result = await comment_service.create_comment("art-1", "user-1", content)

        assert result["content"] == content

    @pytest.mark.asyncio
    async def test_create_comment_response_structure(self, comment_service, mock_comment_repo):
        """COMPLEX: Verify create response has required fields."""
        mock_comment = MagicMock()
        mock_comment.comment_id = "comm-1"
        mock_comment.user_id = "user-1"
        mock_comment.content = "Test"
        mock_comment.created_at = 1234567890

        mock_comment_repo.create.return_value = mock_comment

        result = await comment_service.create_comment("art-1", "user-1", "Test")

        assert "comment_id" in result
        assert "user_id" in result
        assert "content" in result
        assert "created_at" in result
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_create_comment_with_unicode(self, comment_service, mock_comment_repo):
        """HARD: Create comment with unicode characters."""
        content = "文章很好！Очень интересно! 🚀"
        mock_comment = MagicMock()
        mock_comment.comment_id = "comm-1"
        mock_comment.user_id = "user-1"
        mock_comment.content = content
        mock_comment.created_at = 1234567890

        mock_comment_repo.create.return_value = mock_comment

        result = await comment_service.create_comment("art-1", "user-1", content)

        assert result["content"] == content

    @pytest.mark.asyncio
    async def test_create_comment_preserves_data(self, comment_service, mock_comment_repo):
        """COMPLEX: Verify all input data is preserved in output."""
        mock_comment = MagicMock()
        mock_comment.comment_id = "comm-abc-123"
        mock_comment.user_id = "user-xyz-789"
        mock_comment.content = "Specific test content"
        mock_comment.created_at = 9876543210

        mock_comment_repo.create.return_value = mock_comment

        result = await comment_service.create_comment("art-1", "user-xyz-789", "Specific test content")

        assert result["comment_id"] == "comm-abc-123"
        assert result["user_id"] == "user-xyz-789"
        assert result["content"] == "Specific test content"
        assert result["created_at"] == 9876543210


class TestCommentServiceDeleteComment:
    """Tests for deleting comments."""

    @pytest.mark.asyncio
    async def test_delete_comment_basic_success(self, comment_service, mock_comment_repo):
        """BASIC: Successfully delete a comment."""
        mock_comment_repo.delete.return_value = True

        result = await comment_service.delete_comment("comm-1")

        assert result is True
        mock_comment_repo.delete.assert_called_once_with("comm-1")

    @pytest.mark.asyncio
    async def test_delete_comment_not_found(self, comment_service, mock_comment_repo):
        """EDGE: Delete non-existent comment."""
        mock_comment_repo.delete.return_value = False

        result = await comment_service.delete_comment("nonexistent-comm")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_comment_multiple_times(self, comment_service, mock_comment_repo):
        """HARD: Delete same comment multiple times."""
        mock_comment_repo.delete.side_effect = [True, False, False]

        result1 = await comment_service.delete_comment("comm-1")
        result2 = await comment_service.delete_comment("comm-1")
        result3 = await comment_service.delete_comment("comm-1")

        assert result1 is True
        assert result2 is False
        assert result3 is False
        assert mock_comment_repo.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_comment_special_id_format(self, comment_service, mock_comment_repo):
        """COMPLEX: Delete comment with UUID-like ID."""
        comment_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_comment_repo.delete.return_value = True

        result = await comment_service.delete_comment(comment_id)

        assert result is True
        mock_comment_repo.delete.assert_called_once_with(comment_id)

    @pytest.mark.asyncio
    async def test_delete_comment_return_type(self, comment_service, mock_comment_repo):
        """COMPLEX: Verify delete returns boolean."""
        mock_comment_repo.delete.return_value = True

        result = await comment_service.delete_comment("comm-1")

        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_comment_empty_id(self, comment_service, mock_comment_repo):
        """EDGE: Delete comment with empty ID."""
        mock_comment_repo.delete.return_value = False

        result = await comment_service.delete_comment("")

        assert result is False
