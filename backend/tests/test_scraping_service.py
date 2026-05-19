"""Unit tests for ScrapingService."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.scraping_service import ScrapingService


@pytest.mark.asyncio
class TestScrapingService:
    """Test ScrapingService."""

    async def test_scrape_url_empty_url(self):
        """Test scraping with empty URL."""
        service = ScrapingService()
        result = await service.scrape_url("")

        assert result["success"] is False
        assert "empty" in result["error"].lower()
        assert result["markdown_content"] is None
        assert result["raw_html"] is None

    async def test_scrape_url_pdf_url(self):
        """Test scraping with PDF URL."""
        service = ScrapingService()
        result = await service.scrape_url("https://example.com/file.pdf")

        assert result["success"] is False
        assert "pdf" in result["error"].lower()

    @patch("crawl4ai.AsyncWebCrawler")
    async def test_scrape_url_success(self, mock_crawler_class):
        """Test successful URL scraping."""
        # Mock the crawler
        mock_crawler = AsyncMagicMock()
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Article\n\nThis is test content."
        mock_result.html = "<html><body>Test content</body></html>"

        mock_crawler.arun.return_value = mock_result
        mock_crawler_class.return_value = mock_crawler

        service = ScrapingService()
        result = await service.scrape_url("https://techcrunch.com/test-article")

        assert result["success"] is True
        assert result["markdown_content"] == "# Test Article\n\nThis is test content."
        assert "<html>" in result["raw_html"]
        assert result["error"] is None

    @patch("crawl4ai.AsyncWebCrawler")
    async def test_scrape_url_failure(self, mock_crawler_class):
        """Test failed URL scraping."""
        mock_crawler = AsyncMagicMock()
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Network timeout"

        mock_crawler.arun.return_value = mock_result
        mock_crawler_class.return_value = mock_crawler

        service = ScrapingService()
        result = await service.scrape_url("https://invalid.example.com/nonexistent")

        assert result["success"] is False
        assert "Network timeout" in result["error"]

    async def test_scrape_url_import_error(self):
        """Test URL scraping with import error."""
        with patch("builtins.__import__", side_effect=ImportError("Crawl4AI not installed")):
            service = ScrapingService()
            result = await service.scrape_url("https://example.com/article")

            assert result["success"] is False
            assert "not installed" in result["error"].lower()


class AsyncMagicMock(AsyncMock):
    """Helper class for async context manager mocking."""
    pass
