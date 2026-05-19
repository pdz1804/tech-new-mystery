"""Tests for search service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.search_service import SearchService
from app.repositories.article_repository import ArticleRepository


class MockArticle:
    """Mock article for testing."""

    def __init__(
        self,
        article_id,
        title,
        content="",
        summary="",
        tags=None,
        category="General",
        is_published=True,
    ):
        self.article_id = article_id
        self.title = title
        self.slug = title.lower().replace(" ", "-")
        self.content = content
        self.summary = summary
        self.tags = tags or []
        self.category = category
        self.is_published = is_published
        self.published_at = 1234567890
        self.view_count = 100


class TestSearchService:
    """Tests for search service."""

    @pytest.fixture
    def mock_article_repo(self):
        """Create mock article repository."""
        repo = MagicMock(spec=ArticleRepository)
        return repo

    @pytest.fixture
    def service(self, mock_article_repo):
        """Create search service."""
        return SearchService(mock_article_repo)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, service, mock_article_repo):
        """Test search with empty query."""
        result = await service.search("")

        assert result["query"] == ""
        assert result["results"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_search_no_articles(self, service, mock_article_repo):
        """Test search when no articles exist."""
        mock_article_repo.list_all = AsyncMock(return_value=([], None))

        result = await service.search("test")

        assert result["query"] == "test"
        assert result["results"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_search_title_exact_match(self, service, mock_article_repo):
        """Test search with exact title match."""
        article = MockArticle(
            "art-1", "Python Programming Guide", content="Content about Python"
        )
        mock_article_repo.list_all = AsyncMock(return_value=([article], None))

        result = await service.search("python programming guide")

        assert result["total"] == 1
        assert result["results"][0]["title"] == "Python Programming Guide"

    @pytest.mark.asyncio
    async def test_search_title_partial_match(self, service, mock_article_repo):
        """Test search with partial title match."""
        article = MockArticle(
            "art-1", "Python Programming Guide", content="Content"
        )
        mock_article_repo.list_all = AsyncMock(return_value=([article], None))

        result = await service.search("python")

        assert result["total"] == 1
        assert "Python Programming Guide" in result["results"][0]["title"]

    @pytest.mark.asyncio
    async def test_search_content_match(self, service, mock_article_repo):
        """Test search matching content."""
        article = MockArticle(
            "art-1",
            "Article Title",
            content="This article discusses machine learning in detail",
        )
        mock_article_repo.list_all = AsyncMock(return_value=([article], None))

        result = await service.search("machine learning")

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_tag_match(self, service, mock_article_repo):
        """Test search matching tags."""
        article = MockArticle(
            "art-1", "Article", tags=["python", "programming", "tutorial"]
        )
        mock_article_repo.list_all = AsyncMock(return_value=([article], None))

        result = await service.search("python")

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_relevance_scoring(self, service, mock_article_repo):
        """Test that results are ordered by relevance."""
        articles = [
            MockArticle(
                "art-1",
                "Python Programming",
                content="More python content here",
                tags=["python"],
            ),
            MockArticle("art-2", "Java Programming", content="Java content"),
            MockArticle(
                "art-3", "Python Guide", content="Python is great for beginners"
            ),
        ]
        mock_article_repo.list_all = AsyncMock(return_value=(articles, None))

        result = await service.search("python")

        # Should return 2 results, ordered by relevance
        assert result["total"] == 2
        # "Python Programming" should be first (title match)
        assert "Programming" in result["results"][0]["title"]

    @pytest.mark.asyncio
    async def test_search_limit(self, service, mock_article_repo):
        """Test that search respects limit parameter."""
        articles = [
            MockArticle(f"art-{i}", f"Python Article {i}") for i in range(10)
        ]
        mock_article_repo.list_all = AsyncMock(return_value=(articles, None))

        result = await service.search("python", limit=5)

        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_search_category_filter(self, service, mock_article_repo):
        """Test search with category filter."""
        articles = [
            MockArticle(
                "art-1", "Python Guide", category="Technology", is_published=True
            ),
            MockArticle(
                "art-2", "Python in Business", category="Business", is_published=True
            ),
            MockArticle(
                "art-3", "Python Tutorial", category="Technology", is_published=True
            ),
        ]
        mock_article_repo.list_all = AsyncMock(return_value=(articles, None))

        result = await service.search("python", category="Technology")

        assert result["total"] == 2
        for article in result["results"]:
            # Check that all results have the correct category (case insensitive)
            assert article["category"].lower() == "technology"

    @pytest.mark.asyncio
    async def test_search_tags_filter(self, service, mock_article_repo):
        """Test search with tags filter."""
        articles = [
            MockArticle("art-1", "Article 1", tags=["python", "tutorial"]),
            MockArticle("art-2", "Article 2", tags=["javascript", "tutorial"]),
            MockArticle("art-3", "Article 3", tags=["python", "advanced"]),
        ]
        mock_article_repo.list_all = AsyncMock(return_value=(articles, None))

        result = await service.search("tutorial", tags=["python"])

        # Should return only articles with both 'tutorial' and 'python' tags
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_excludes_unpublished(self, service, mock_article_repo):
        """Test that search excludes unpublished articles."""
        articles = [
            MockArticle("art-1", "Published Article", is_published=True),
            MockArticle("art-2", "Draft Article", is_published=False),
        ]
        mock_article_repo.list_all = AsyncMock(return_value=(articles, None))

        result = await service.search("article")

        assert result["total"] == 1
        assert result["results"][0]["article_id"] == "art-1"

    @pytest.mark.asyncio
    async def test_search_handles_missing_fields(self, service, mock_article_repo):
        """Test search handles articles with missing optional fields."""
        article = MagicMock()
        article.article_id = "art-1"
        article.title = "Article"
        article.slug = "article"
        article.is_published = True
        article.content = None
        article.summary = None
        article.tags = []
        article.category = "General"

        mock_article_repo.list_all = AsyncMock(return_value=([article], None))

        result = await service.search("article")

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, service, mock_article_repo):
        """Test that search is case insensitive."""
        article = MockArticle("art-1", "PYTHON Programming", content="Content")
        mock_article_repo.list_all = AsyncMock(return_value=([article], None))

        result = await service.search("python")

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_error_handling(self, service, mock_article_repo):
        """Test search handles errors gracefully."""
        mock_article_repo.list_all = AsyncMock(side_effect=Exception("DB Error"))

        result = await service.search("test")

        assert result["total"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_format_article(self, service):
        """Test article formatting."""
        article = MockArticle(
            "art-1",
            "Test Article",
            summary="Test summary",
            category="Tech",
            tags=["tag1", "tag2"],
        )

        formatted = service._format_article(article)

        assert formatted["article_id"] == "art-1"
        assert formatted["title"] == "Test Article"
        assert formatted["category"] == "Tech"
        assert len(formatted["tags"]) == 2

    @pytest.mark.asyncio
    async def test_search_relevance_score_calculation(self, service):
        """Test relevance score calculation."""
        article = MockArticle(
            "art-1",
            "Python Programming",
            content="Learn Python programming basics",
            summary="Python is great",
            tags=["python"],
        )

        score = service._calculate_relevance_score(article, "python")

        # Score should be > 0
        assert score > 0
        # Title contains query should give points
        assert score > 15  # At least tag match points
