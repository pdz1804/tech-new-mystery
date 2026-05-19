"""Tests for crawling tasks."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from app.workers.tasks.crawl_tasks import _crawl_all_sources, _crawl_source
from app.integrations.crawler_client import CrawledContent


@pytest.fixture
def mock_crawler():
    """Mock crawler client."""
    crawler = AsyncMock()
    return crawler


@pytest.fixture
def mock_article_repo():
    """Mock article repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_source_repo():
    """Mock source repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def sample_source():
    """Sample news source."""
    source = MagicMock()
    source.source_id = "source-1"
    source.name = "Tech News Daily"
    source.url = "https://technewsdaily.com"
    source.enabled = True
    source.category = "Technology"
    return source


@pytest.fixture
def sample_crawled_content():
    """Sample crawled content."""
    return CrawledContent(
        url="https://technewsdaily.com/article1",
        title="Breaking: AI Breakthrough",
        content="This is the article content about AI...",
        markdown="# Breaking: AI Breakthrough\n\nThis is the article content about AI...",
        cleaned_html="<article>...</article>",
        success=True,
    )


class TestCrawlSource:
    """Tests for _crawl_source function."""

    @pytest.mark.asyncio
    async def test_crawl_source_success(
        self, sample_source, sample_crawled_content, mock_crawler, mock_article_repo
    ):
        """Test successful source crawl."""
        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.get.return_value = sample_source
            mock_source_repo_class.return_value = mock_source_repo

            mock_crawler.crawl_url.return_value = sample_crawled_content
            mock_article_repo.get_by_slug.return_value = None

            created_article = MagicMock()
            created_article.article_id = str(uuid.uuid4())
            created_article.title = sample_crawled_content.title
            created_article.content = sample_crawled_content.content
            mock_article_repo.create.return_value = created_article

            result = await _crawl_source("source-1")

            assert result["success"] is True
            assert result["source_id"] == "source-1"
            assert result["article_id"] == created_article.article_id
            assert result["title"] == sample_crawled_content.title
            mock_crawler.crawl_url.assert_called_once()
            mock_article_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_source_not_found(self, mock_crawler, mock_article_repo):
        """Test crawl when source not found."""
        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.get.return_value = None
            mock_source_repo_class.return_value = mock_source_repo

            result = await _crawl_source("nonexistent-source")

            assert result["success"] is False
            assert "not found" in result["error"].lower()
            mock_crawler.crawl_url.assert_not_called()

    @pytest.mark.asyncio
    async def test_crawl_source_no_url(self, mock_crawler, mock_article_repo):
        """Test crawl when source has no URL."""
        source = MagicMock()
        source.source_id = "source-1"
        source.url = None

        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.get.return_value = source
            mock_source_repo_class.return_value = mock_source_repo

            result = await _crawl_source("source-1")

            assert result["success"] is False
            assert "no URL" in result["error"]

    @pytest.mark.asyncio
    async def test_crawl_source_crawl_failure(self, sample_source, mock_crawler, mock_article_repo):
        """Test handling of crawl failure."""
        failed_crawl = CrawledContent(
            url="https://technewsdaily.com",
            title=None,
            content="",
            markdown="",
            cleaned_html=None,
            error="Connection timeout",
            success=False,
        )

        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.get.return_value = sample_source
            mock_source_repo_class.return_value = mock_source_repo

            mock_crawler.crawl_url.return_value = failed_crawl

            result = await _crawl_source("source-1")

            assert result["success"] is False
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_crawl_source_deduplication(
        self, sample_source, sample_crawled_content, mock_crawler, mock_article_repo
    ):
        """Test that duplicate articles are not created."""
        existing_article = MagicMock()
        existing_article.article_id = "existing-id"

        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.get.return_value = sample_source
            mock_source_repo_class.return_value = mock_source_repo

            mock_crawler.crawl_url.return_value = sample_crawled_content
            mock_article_repo.get_by_slug.return_value = existing_article

            result = await _crawl_source("source-1")

            assert result["success"] is True
            assert result["status"] == "skipped"
            assert "already exists" in result["reason"].lower()
            mock_article_repo.create.assert_not_called()


class TestCrawlAllSources:
    """Tests for _crawl_all_sources function."""

    @pytest.mark.asyncio
    async def test_crawl_all_sources_success(
        self, sample_source, sample_crawled_content, mock_crawler, mock_article_repo
    ):
        """Test successful crawl of all sources."""
        sources = [sample_source]

        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.list.return_value = sources
            mock_source_repo_class.return_value = mock_source_repo

            mock_crawler.crawl_url.return_value = sample_crawled_content
            mock_article_repo.get_by_slug.return_value = None

            created_article = MagicMock()
            created_article.article_id = str(uuid.uuid4())
            created_article.title = sample_crawled_content.title
            mock_article_repo.create.return_value = created_article

            result = await _crawl_all_sources()

            assert result["total"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            assert result["articles_created"] == 1
            assert result["articles_skipped"] == 0

    @pytest.mark.asyncio
    async def test_crawl_all_sources_mixed_results(
        self, sample_source, sample_crawled_content, mock_crawler, mock_article_repo
    ):
        """Test crawl with mixed success and failure."""
        source1 = sample_source
        source2 = MagicMock()
        source2.source_id = "source-2"
        source2.name = "Bad News Site"
        source2.url = "https://badnews.com"
        source2.enabled = True
        source2.category = "General"

        sources = [source1, source2]
        failed_crawl = CrawledContent(
            url="https://badnews.com",
            title=None,
            content="",
            markdown="",
            cleaned_html=None,
            error="Connection refused",
            success=False,
        )

        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.list.return_value = sources
            mock_source_repo_class.return_value = mock_source_repo

            # First source succeeds, second fails
            mock_crawler.crawl_url.side_effect = [
                sample_crawled_content,
                failed_crawl,
            ]
            mock_article_repo.get_by_slug.return_value = None

            created_article = MagicMock()
            created_article.article_id = str(uuid.uuid4())
            mock_article_repo.create.return_value = created_article

            result = await _crawl_all_sources()

            assert result["total"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1
            assert result["articles_created"] == 1
            assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_crawl_all_sources_with_duplicates(
        self, sample_source, sample_crawled_content, mock_crawler, mock_article_repo
    ):
        """Test crawl that finds duplicate articles."""
        sources = [sample_source, sample_source]  # Same source twice
        existing_article = MagicMock()
        existing_article.article_id = "existing-id"

        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.list.return_value = sources
            mock_source_repo_class.return_value = mock_source_repo

            mock_crawler.crawl_url.side_effect = [
                sample_crawled_content,
                sample_crawled_content,
            ]

            # First call returns None (new article), second returns existing
            mock_article_repo.get_by_slug.side_effect = [None, existing_article]

            created_article = MagicMock()
            created_article.article_id = str(uuid.uuid4())
            mock_article_repo.create.return_value = created_article

            result = await _crawl_all_sources()

            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["articles_created"] == 1
            assert result["articles_skipped"] == 1

    @pytest.mark.asyncio
    async def test_crawl_all_sources_empty_sources(self, mock_crawler, mock_article_repo):
        """Test crawl when no sources are enabled."""
        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.list.return_value = []
            mock_source_repo_class.return_value = mock_source_repo

            result = await _crawl_all_sources()

            assert result["total"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0
            assert result["articles_created"] == 0

    @pytest.mark.asyncio
    async def test_crawl_all_sources_source_no_url(self, mock_crawler, mock_article_repo):
        """Test handling source with no URL."""
        source = MagicMock()
        source.source_id = "source-1"
        source.name = "No URL Source"
        source.url = None
        source.enabled = True

        with patch(
            "app.workers.tasks.crawl_tasks.get_crawler_client",
            return_value=mock_crawler,
        ), patch(
            "app.workers.tasks.crawl_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.crawl_tasks.NewsSourceRepository"
        ) as mock_source_repo_class:
            mock_source_repo = AsyncMock()
            mock_source_repo.list.return_value = [source]
            mock_source_repo_class.return_value = mock_source_repo

            result = await _crawl_all_sources()

            assert result["total"] == 1
            assert result["successful"] == 0
            assert result["failed"] == 1
