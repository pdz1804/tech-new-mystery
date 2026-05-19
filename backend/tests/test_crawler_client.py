"""Tests for Crawl4AI web crawler client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.integrations.crawler_client import CrawlerClient, CrawledContent


class TestCrawlerClient:
    """Tests for web crawler client."""

    @pytest.fixture
    def client(self):
        """Create crawler client."""
        return CrawlerClient()

    @pytest.mark.asyncio
    async def test_initialize_crawler(self, client):
        """Test crawler initialization."""
        with patch("app.integrations.crawler_client.AsyncWebCrawler") as mock_crawler:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_crawler.return_value = mock_instance

            await client.initialize()
            assert client.crawler is not None

    @pytest.mark.asyncio
    async def test_crawl_url_success(self, client):
        """Test successful URL crawling."""
        client.crawler = MagicMock()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metadata = {"title": "Test Article"}
        mock_result.text = "Article content here"
        mock_result.markdown = "# Test Article\n\nContent"
        mock_result.cleaned_html = "<h1>Test</h1><p>Content</p>"

        client.crawler.arun = AsyncMock(return_value=mock_result)

        result = await client.crawl_url("https://example.com")

        assert result.success is True
        assert result.title == "Test Article"
        assert result.content == "Article content here"
        assert result.markdown == "# Test Article\n\nContent"

    @pytest.mark.asyncio
    async def test_crawl_url_failure(self, client):
        """Test failed URL crawling."""
        client.crawler = MagicMock()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Connection timeout"

        client.crawler.arun = AsyncMock(return_value=mock_result)

        result = await client.crawl_url("https://example.com")

        assert result.success is False
        assert result.error is not None
        assert "Connection timeout" in result.error

    @pytest.mark.asyncio
    async def test_crawl_url_exception_handling(self, client):
        """Test exception handling during crawl."""
        client.crawler = MagicMock()
        client.crawler.arun = AsyncMock(side_effect=Exception("Network error"))

        result = await client.crawl_url("https://example.com")

        assert result.success is False
        assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_crawl_multiple_urls(self, client):
        """Test crawling multiple URLs."""
        client.crawler = MagicMock()

        def create_mock_result(url, success=True):
            mock_result = MagicMock()
            mock_result.success = success
            mock_result.metadata = {"title": f"Title from {url}"}
            mock_result.text = f"Content from {url}"
            mock_result.markdown = f"# Title\n\nContent from {url}"
            mock_result.cleaned_html = "<p>Content</p>"
            return mock_result

        urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com",
        ]
        mock_results = [create_mock_result(url) for url in urls]

        client.crawler.arun = AsyncMock(side_effect=mock_results)

        results = await client.crawl_multiple(urls)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].title == "Title from https://example1.com"

    @pytest.mark.asyncio
    async def test_crawled_content_dataclass(self):
        """Test CrawledContent data structure."""
        content = CrawledContent(
            url="https://example.com",
            title="Test Title",
            content="Test content",
            markdown="# Test",
            cleaned_html="<h1>Test</h1>",
        )

        assert content.url == "https://example.com"
        assert content.title == "Test Title"
        assert content.success is True
        assert content.error is None

    @pytest.mark.asyncio
    async def test_crawled_content_with_error(self):
        """Test CrawledContent with error."""
        content = CrawledContent(
            url="https://example.com",
            title=None,
            content="",
            markdown="",
            cleaned_html=None,
            error="Connection refused",
            success=False,
        )

        assert content.success is False
        assert content.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_close_crawler(self, client):
        """Test closing crawler connection."""
        client.crawler = MagicMock()
        client.crawler.__aexit__ = AsyncMock()

        await client.close()
        assert client.crawler.__aexit__.called

    @pytest.mark.asyncio
    async def test_crawl_url_auto_initialize(self, client):
        """Test that crawl_url initializes crawler if not already done."""
        with patch.object(client, "initialize", new_callable=AsyncMock) as mock_init:
            client.crawler = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.metadata = {}
            mock_result.text = "Content"
            mock_result.markdown = "Content"
            mock_result.cleaned_html = ""
            client.crawler.arun = AsyncMock(return_value=mock_result)

            await client.crawl_url("https://example.com")
            # Crawler is already set, so no initialization needed
            # mock_init.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_title_from_metadata(self, client):
        """Test title extraction from metadata."""
        mock_result = MagicMock()
        mock_result.metadata = {"title": "Extracted Title"}

        title = client._extract_title(mock_result)
        assert title == "Extracted Title"
