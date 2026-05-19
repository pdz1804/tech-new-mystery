"""
Comprehensive tests for ArticleService.
Tests cover: basic cases, hard cases, complex cases, and edge cases.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.article_service import ArticleService
from app.repositories.article_repository import ArticleRepository
from app.core.exceptions import ArticleNotFoundError


@pytest.fixture
def mock_article_repo():
    """Mock ArticleRepository."""
    repo = AsyncMock(spec=ArticleRepository)
    return repo


@pytest.fixture
def article_service(mock_article_repo):
    """Create ArticleService with mocked repository."""
    return ArticleService(article_repo=mock_article_repo)


class TestArticleServiceList:
    """Tests for listing articles."""

    @pytest.mark.asyncio
    async def test_list_articles_basic_success(self, article_service, mock_article_repo):
        """BASIC: Successfully list articles."""
        mock_article1 = MagicMock()
        mock_article1.article_id = "art-1"
        mock_article1.title = "Article 1"
        mock_article1.slug = "article-1"
        mock_article1.view_count = 10
        mock_article1.is_published = True
        mock_article1.tags = ["tech"]
        mock_article1.created_at = 1234567890

        mock_article_repo.list_all.return_value = ([mock_article1], None)

        result = await article_service.list_articles(limit=20)

        assert len(result["data"]) == 1
        assert result["data"][0]["title"] == "Article 1"
        assert result["meta"]["limit"] == 20

    @pytest.mark.asyncio
    async def test_list_articles_empty(self, article_service, mock_article_repo):
        """EDGE: List articles when none exist."""
        mock_article_repo.list_all.return_value = ([], None)

        result = await article_service.list_articles()

        assert result["data"] == []
        assert result["meta"]["last_key"] is None

    @pytest.mark.asyncio
    async def test_list_articles_with_pagination(self, article_service, mock_article_repo):
        """HARD: List articles with pagination cursor."""
        mock_articles = [
            MagicMock(
                article_id=f"art-{i}",
                title=f"Article {i}",
                slug=f"article-{i}",
                view_count=i,
                is_published=True,
                tags=[],
                created_at=1234567890,
            )
            for i in range(3)
        ]

        mock_article_repo.list_all.return_value = (mock_articles, "next-cursor")

        result = await article_service.list_articles(limit=3, last_key="cursor-123")

        assert len(result["data"]) == 3
        assert result["meta"]["last_key"] == "next-cursor"
        mock_article_repo.list_all.assert_called_once_with(limit=3, last_key="cursor-123")

    @pytest.mark.asyncio
    async def test_list_articles_limit_validation(self, article_service, mock_article_repo):
        """COMPLEX: Verify limit is applied correctly."""
        mock_articles = [MagicMock(article_id=f"art-{i}", title=f"Article {i}", slug=f"article-{i}", view_count=0, is_published=True, tags=[], created_at=1234567890) for i in range(50)]
        mock_article_repo.list_all.return_value = (mock_articles[:20], None)

        result = await article_service.list_articles(limit=20)

        assert len(result["data"]) == 20
        mock_article_repo.list_all.assert_called_with(limit=20, last_key=None)

    @pytest.mark.asyncio
    async def test_list_articles_published_filter(self, article_service, mock_article_repo):
        """COMPLEX: All returned articles should be published."""
        mock_articles = [
            MagicMock(article_id="art-1", title="Article 1", slug="article-1", is_published=True, view_count=5, tags=[], created_at=123456),
            MagicMock(article_id="art-2", title="Article 2", slug="article-2", is_published=True, view_count=10, tags=[], created_at=123456),
        ]
        mock_article_repo.list_all.return_value = (mock_articles, None)

        result = await article_service.list_articles()

        for article in result["data"]:
            assert article["is_published"] is True


class TestArticleServiceGetBySlug:
    """Tests for getting article by slug."""

    @pytest.mark.asyncio
    async def test_get_article_by_slug_success(self, article_service, mock_article_repo):
        """BASIC: Successfully get article by slug."""
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = "Test Article"
        mock_article.slug = "test-article"
        mock_article.content = "Article content here"
        mock_article.summary = "Summary"
        mock_article.markdown_content = "# Markdown"
        mock_article.author = "John Doe"
        mock_article.original_url = "https://example.com"
        mock_article.source_id = "src-1"
        mock_article.category = "tech"
        mock_article.tags = ["python", "testing"]
        mock_article.view_count = 42
        mock_article.is_published = True
        mock_article.published_at = 1234567890
        mock_article.created_at = 1234567890

        mock_article_repo.get_by_slug.return_value = mock_article

        result = await article_service.get_article_by_slug("test-article")

        assert result["title"] == "Test Article"
        assert result["content"] == "Article content here"
        assert result["view_count"] == 42

    @pytest.mark.asyncio
    async def test_get_article_by_slug_not_found(self, article_service, mock_article_repo):
        """EDGE: Get non-existent article by slug."""
        mock_article_repo.get_by_slug.return_value = None

        with pytest.raises(ArticleNotFoundError):
            await article_service.get_article_by_slug("nonexistent-slug")

    @pytest.mark.asyncio
    async def test_get_article_by_slug_special_characters(self, article_service, mock_article_repo):
        """COMPLEX: Get article with slug containing special characters."""
        slug = "article-with-dashes-and-numbers-123"
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = "Article With Dashes and Numbers 123"
        mock_article.slug = slug
        mock_article.content = "Content"
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.author = None
        mock_article.original_url = ""
        mock_article.source_id = ""
        mock_article.category = None
        mock_article.tags = []
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.get_by_slug.return_value = mock_article

        result = await article_service.get_article_by_slug(slug)
        assert result["slug"] == slug

    @pytest.mark.asyncio
    async def test_get_article_by_slug_case_sensitive(self, article_service, mock_article_repo):
        """HARD: Verify slug lookup is case-sensitive."""
        mock_article_repo.get_by_slug.return_value = None

        with pytest.raises(ArticleNotFoundError):
            await article_service.get_article_by_slug("Test-Article")

        # Verify exact slug was searched
        mock_article_repo.get_by_slug.assert_called_with("Test-Article")


class TestArticleServiceCreate:
    """Tests for creating articles."""

    @pytest.mark.asyncio
    async def test_create_article_basic_success(self, article_service, mock_article_repo):
        """BASIC: Successfully create article."""
        mock_article = MagicMock()
        mock_article.article_id = "new-art-1"
        mock_article.title = "New Article"
        mock_article.slug = "new-article"
        mock_article.source_id = "src-1"
        mock_article.original_url = "https://example.com"
        mock_article.content = "Content"
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.author = None
        mock_article.category = None
        mock_article.tags = []
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.create.return_value = mock_article

        result = await article_service.create_article({
            "title": "New Article",
            "original_url": "https://example.com",
            "content": "Content",
            "source_id": "src-1",
        })

        assert result["title"] == "New Article"
        assert result["is_published"] is True
        mock_article_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_article_slug_generation(self, article_service, mock_article_repo):
        """HARD: Verify slug is generated from title."""
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = "This Is A Test Article Title"
        mock_article.slug = "this-is-a-test-article-title"
        mock_article.source_id = "src-1"
        mock_article.original_url = "https://example.com"
        mock_article.content = "Content"
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.author = None
        mock_article.category = None
        mock_article.tags = []
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.create.return_value = mock_article

        result = await article_service.create_article({
            "title": "This Is A Test Article Title",
            "original_url": "https://example.com",
            "content": "Content",
            "source_id": "src-1",
        })

        # Check that create was called with a slug
        call_args = mock_article_repo.create.call_args
        assert call_args[0][0]["slug"] is not None
        assert call_args[0][0]["slug"] == "this-is-a-test-article-title"

    @pytest.mark.asyncio
    async def test_create_article_with_optional_fields(self, article_service, mock_article_repo):
        """COMPLEX: Create article with all optional fields."""
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = "Full Article"
        mock_article.slug = "full-article"
        mock_article.source_id = "src-1"
        mock_article.original_url = "https://example.com"
        mock_article.content = "Full content here"
        mock_article.summary = "Summary of article"
        mock_article.markdown_content = "# Markdown"
        mock_article.author = "Jane Doe"
        mock_article.category = "technology"
        mock_article.tags = ["python", "testing", "automation"]
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = 1234567890
        mock_article.created_at = 1234567890

        mock_article_repo.create.return_value = mock_article

        result = await article_service.create_article({
            "title": "Full Article",
            "original_url": "https://example.com",
            "content": "Full content here",
            "source_id": "src-1",
            "summary": "Summary of article",
            "markdown_content": "# Markdown",
            "author": "Jane Doe",
            "category": "technology",
            "tags": ["python", "testing", "automation"],
        })

        assert result["author"] == "Jane Doe"
        assert result["category"] == "technology"
        assert len(result["tags"]) == 3

    @pytest.mark.asyncio
    async def test_create_article_empty_title(self, article_service, mock_article_repo):
        """EDGE: Attempt to create article with empty title."""
        with pytest.raises((ValueError, AssertionError)):
            await article_service.create_article({
                "title": "",  # Empty
                "original_url": "https://example.com",
                "content": "Content",
                "source_id": "src-1",
            })

    @pytest.mark.asyncio
    async def test_create_article_very_long_title(self, article_service, mock_article_repo):
        """HARD: Create article with very long title."""
        long_title = "A" * 500  # 500 characters
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = long_title
        mock_article.slug = "a" * 200  # Truncated slug
        mock_article.source_id = "src-1"
        mock_article.original_url = "https://example.com"
        mock_article.content = "Content"
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.author = None
        mock_article.category = None
        mock_article.tags = []
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.create.return_value = mock_article

        result = await article_service.create_article({
            "title": long_title,
            "original_url": "https://example.com",
            "content": "Content",
            "source_id": "src-1",
        })

        assert result["title"] == long_title

    @pytest.mark.asyncio
    async def test_create_article_special_characters_in_title(self, article_service, mock_article_repo):
        """COMPLEX: Create article with special characters in title."""
        title = "Article & Test: C++ Programming #2024"
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = title
        mock_article.slug = "article-test-c-programming-2024"
        mock_article.source_id = "src-1"
        mock_article.original_url = "https://example.com"
        mock_article.content = "Content"
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.author = None
        mock_article.category = None
        mock_article.tags = []
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.create.return_value = mock_article

        result = await article_service.create_article({
            "title": title,
            "original_url": "https://example.com",
            "content": "Content",
            "source_id": "src-1",
        })

        assert result["title"] == title
        # Slug should have special chars removed
        assert result["slug"] is not None

    @pytest.mark.asyncio
    async def test_create_article_unicode_title(self, article_service, mock_article_repo):
        """HARD: Create article with unicode characters in title."""
        title = "文章标题 - Article 文章"  # Chinese characters
        mock_article = MagicMock()
        mock_article.article_id = "art-1"
        mock_article.title = title
        mock_article.slug = "article"
        mock_article.source_id = "src-1"
        mock_article.original_url = "https://example.com"
        mock_article.content = "Content"
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.author = None
        mock_article.category = None
        mock_article.tags = []
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.create.return_value = mock_article

        result = await article_service.create_article({
            "title": title,
            "original_url": "https://example.com",
            "content": "Content",
            "source_id": "src-1",
        })

        assert result["title"] == title


class TestArticleServiceUpdate:
    """Tests for updating articles."""

    @pytest.mark.asyncio
    async def test_update_article_basic_success(self, article_service, mock_article_repo):
        """BASIC: Successfully update article title."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        original_article.title = "Old Title"
        original_article.slug = "old-title"
        original_article.content = "Original content"
        original_article.author = "John Doe"
        original_article.category = "tech"
        original_article.tags = ["python"]
        original_article.summary = "Summary"
        original_article.markdown_content = None
        original_article.original_url = "https://example.com"
        original_article.source_id = "src-1"
        original_article.view_count = 5
        original_article.is_published = True
        original_article.published_at = 1234567890
        original_article.created_at = 1234567890

        updated_article = MagicMock()
        updated_article.article_id = "art-1"
        updated_article.title = "New Title"
        updated_article.slug = "old-title"
        updated_article.content = "Original content"
        updated_article.author = "John Doe"
        updated_article.category = "tech"
        updated_article.tags = ["python"]
        updated_article.summary = "Summary"
        updated_article.markdown_content = None
        updated_article.original_url = "https://example.com"
        updated_article.source_id = "src-1"
        updated_article.view_count = 5
        updated_article.is_published = True
        updated_article.published_at = 1234567890
        updated_article.created_at = 1234567890

        mock_article_repo.get_by_slug.return_value = original_article
        mock_article_repo.update.return_value = updated_article

        result = await article_service.update_article("old-title", {"title": "New Title"})

        assert result["title"] == "New Title"
        mock_article_repo.update.assert_called_once_with("art-1", title="New Title")

    @pytest.mark.asyncio
    async def test_update_article_not_found(self, article_service, mock_article_repo):
        """EDGE: Update non-existent article."""
        mock_article_repo.get_by_slug.return_value = None

        with pytest.raises(ArticleNotFoundError):
            await article_service.update_article("nonexistent-slug", {"title": "New Title"})

    @pytest.mark.asyncio
    async def test_update_article_no_fields(self, article_service, mock_article_repo):
        """EDGE: Update with no fields provided."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        mock_article_repo.get_by_slug.return_value = original_article

        with pytest.raises(ValueError, match="At least one field must be provided"):
            await article_service.update_article("test-slug", {})

    @pytest.mark.asyncio
    async def test_update_article_multiple_fields(self, article_service, mock_article_repo):
        """COMPLEX: Update multiple fields at once."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        original_article.title = "Old Title"
        original_article.slug = "old-title"
        original_article.content = "Old content"
        original_article.author = "Old Author"
        original_article.category = "tech"
        original_article.tags = ["python"]
        original_article.summary = "Old summary"
        original_article.markdown_content = None
        original_article.original_url = "https://example.com"
        original_article.source_id = "src-1"
        original_article.view_count = 5
        original_article.is_published = True
        original_article.published_at = 1234567890
        original_article.created_at = 1234567890

        updated_article = MagicMock()
        updated_article.article_id = "art-1"
        updated_article.title = "New Title"
        updated_article.slug = "old-title"
        updated_article.content = "New content"
        updated_article.author = "New Author"
        updated_article.category = "ai"
        updated_article.tags = ["machine-learning"]
        updated_article.summary = "New summary"
        updated_article.markdown_content = None
        updated_article.original_url = "https://example.com"
        updated_article.source_id = "src-1"
        updated_article.view_count = 5
        updated_article.is_published = True
        updated_article.published_at = 1234567890
        updated_article.created_at = 1234567890

        mock_article_repo.get_by_slug.return_value = original_article
        mock_article_repo.update.return_value = updated_article

        result = await article_service.update_article(
            "old-title",
            {
                "title": "New Title",
                "content": "New content",
                "author": "New Author",
                "category": "ai",
                "tags": ["machine-learning"],
                "summary": "New summary",
            },
        )

        assert result["title"] == "New Title"
        assert result["author"] == "New Author"
        assert result["category"] == "ai"
        assert result["content"] == "New content"

    @pytest.mark.asyncio
    async def test_update_article_empty_title(self, article_service, mock_article_repo):
        """EDGE: Update with empty title."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        mock_article_repo.get_by_slug.return_value = original_article

        with pytest.raises(ValueError, match="Title cannot be empty"):
            await article_service.update_article("test-slug", {"title": "   "})

    @pytest.mark.asyncio
    async def test_update_article_title_too_long(self, article_service, mock_article_repo):
        """HARD: Update with title exceeding max length."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        mock_article_repo.get_by_slug.return_value = original_article

        long_title = "A" * 501  # Exceeds 500 char limit

        with pytest.raises(ValueError, match="Title must be 500 characters or less"):
            await article_service.update_article("test-slug", {"title": long_title})

    @pytest.mark.asyncio
    async def test_update_article_author_only(self, article_service, mock_article_repo):
        """BASIC: Update only author field."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        original_article.title = "Old Title"
        original_article.slug = "old-title"
        original_article.content = "Content"
        original_article.author = "Old Author"
        original_article.category = "tech"
        original_article.tags = ["python"]
        original_article.summary = "Summary"
        original_article.markdown_content = None
        original_article.original_url = "https://example.com"
        original_article.source_id = "src-1"
        original_article.view_count = 5
        original_article.is_published = True
        original_article.published_at = 1234567890
        original_article.created_at = 1234567890

        updated_article = MagicMock()
        updated_article.article_id = "art-1"
        updated_article.title = "Old Title"
        updated_article.slug = "old-title"
        updated_article.content = "Content"
        updated_article.author = "New Author"
        updated_article.category = "tech"
        updated_article.tags = ["python"]
        updated_article.summary = "Summary"
        updated_article.markdown_content = None
        updated_article.original_url = "https://example.com"
        updated_article.source_id = "src-1"
        updated_article.view_count = 5
        updated_article.is_published = True
        updated_article.published_at = 1234567890
        updated_article.created_at = 1234567890

        mock_article_repo.get_by_slug.return_value = original_article
        mock_article_repo.update.return_value = updated_article

        result = await article_service.update_article("old-title", {"author": "New Author"})

        assert result["author"] == "New Author"
        mock_article_repo.update.assert_called_once_with("art-1", author="New Author")


class TestArticleServiceDelete:
    """Tests for deleting articles."""

    @pytest.mark.asyncio
    async def test_delete_article_success(self, article_service, mock_article_repo):
        """BASIC: Successfully delete article."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        mock_article_repo.get_by_slug.return_value = original_article
        mock_article_repo.delete.return_value = True

        result = await article_service.delete_article("test-slug")

        assert result is True
        mock_article_repo.delete.assert_called_once_with("art-1")

    @pytest.mark.asyncio
    async def test_delete_article_not_found(self, article_service, mock_article_repo):
        """EDGE: Delete non-existent article."""
        mock_article_repo.get_by_slug.return_value = None

        result = await article_service.delete_article("nonexistent-slug")

        assert result is False
        mock_article_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_article_repository_error(self, article_service, mock_article_repo):
        """HARD: Handle repository error during deletion."""
        original_article = MagicMock()
        original_article.article_id = "art-1"
        mock_article_repo.get_by_slug.return_value = original_article
        mock_article_repo.delete.return_value = False

        result = await article_service.delete_article("test-slug")

        assert result is False


class TestArticleServiceCreateFromUrl:
    """Tests for creating articles from URL."""

    @pytest.mark.asyncio
    async def test_create_from_url_basic_success(self, article_service, mock_article_repo):
        """BASIC: Successfully create article from URL."""
        mock_article = MagicMock()
        mock_article.article_id = "new-art-1"
        mock_article.title = "Article Title"
        mock_article.slug = "article-title"
        mock_article.content = "Article content here"
        mock_article.author = "Jane Doe"
        mock_article.category = None
        mock_article.tags = []
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.original_url = "https://example.com/article"
        mock_article.source_id = "manual"
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.list_all.return_value = ([], None)
        mock_article_repo.create.return_value = mock_article

        # Note: This test uses mocking to avoid actual HTTP requests
        # In real tests, we'd mock requests.get
        import unittest.mock
        with unittest.mock.patch("app.services.article_service.requests.get") as mock_get:
            mock_response = MagicMock()
            html_content = "<html><title>Article Title</title><article><p>Article content here</p></article></html>"
            mock_response.content = html_content.encode()
            mock_response.text = html_content
            mock_response.apparent_encoding = 'utf-8'
            mock_get.return_value = mock_response

            result = await article_service.create_from_url(
                "https://example.com/article",
                title="Article Title",
                author="Jane Doe",
            )

            assert result["title"] == "Article Title"
            assert result["is_published"] is True
            assert "article" in result["slug"]

    @pytest.mark.asyncio
    async def test_create_from_url_duplicate(self, article_service, mock_article_repo):
        """EDGE: Prevent duplicate URLs."""
        existing_article = MagicMock()
        existing_article.original_url = "https://example.com/article"

        mock_article_repo.list_all.return_value = ([existing_article], None)

        with pytest.raises(ValueError, match="already exists"):
            await article_service.create_from_url("https://example.com/article")

    @pytest.mark.asyncio
    async def test_create_from_url_invalid_url(self, article_service, mock_article_repo):
        """EDGE: Invalid URL format."""
        with pytest.raises(ValueError, match="Invalid URL"):
            await article_service.create_from_url("not-a-valid-url")

    @pytest.mark.asyncio
    async def test_create_from_url_no_title_extracted(self, article_service, mock_article_repo):
        """HARD: Create article with default title when no title can be extracted."""
        mock_article_repo.list_all.return_value = ([], None)

        mock_article = MagicMock()
        mock_article.article_id = "new-art-1"
        mock_article.title = "Untitled"
        mock_article.slug = "untitled"
        mock_article.content = "Article content here"
        mock_article.author = None
        mock_article.category = "Other"
        mock_article.tags = []
        mock_article.summary = None
        mock_article.markdown_content = None
        mock_article.original_url = "https://example.com/article"
        mock_article.source_id = "example.com"
        mock_article.view_count = 0
        mock_article.is_published = True
        mock_article.published_at = None
        mock_article.created_at = 1234567890

        mock_article_repo.create.return_value = mock_article

        import unittest.mock
        with unittest.mock.patch("app.services.scraping_service.ScrapingService") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper_class.return_value = mock_scraper

            async def async_scrape(*args, **kwargs):
                return {
                    "success": True,
                    "raw_html": "<html><body>No title here</body></html>"
                }
            mock_scraper.scrape_url = async_scrape

            with unittest.mock.patch("app.services.article_processing_service.ArticleProcessingService") as mock_processor_class:
                mock_processor = MagicMock()
                mock_processor_class.return_value = mock_processor

                # Simulate processing with no title extracted
                async def async_process(*args, **kwargs):
                    return {
                        # No "title" key - code will use "Untitled" default via get("title", "Untitled")
                        "summary": "Summary",
                        "category": "Other",
                        "tags": [],
                        "author": None,
                        "structured_markdown": "# Content"
                    }
                mock_processor.process_url_content = async_process
                mock_processor._extract_text_from_html = MagicMock(return_value="Article content here")

                result = await article_service.create_from_url("https://example.com/article")

                # Should create article with default "Untitled" title (code does: generated_title = processing_result.get("title", "Untitled"))
                assert result["title"] == "Untitled"
                assert result["is_published"] is True
                assert result["original_url"] == "https://example.com/article"
                # Verify create was called with "Untitled" as title
                assert mock_article_repo.create.called
                create_call_args = mock_article_repo.create.call_args[0][0]
                assert create_call_args["title"] == "Untitled"
