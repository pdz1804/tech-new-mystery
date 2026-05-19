"""Unit tests for Tavily search integration in SearchService."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.search_service import SearchService
from app.repositories.article_repository import ArticleRepository


@pytest.mark.asyncio
class TestTavilySearch:
    """Test Tavily search functionality."""

    async def test_tavily_search_empty_query(self):
        """Test Tavily search with empty query."""
        service = SearchService(ArticleRepository())
        result = await service.tavily_search("")

        assert result["success"] is False
        assert result["count"] == 0
        assert "empty" in result["error"].lower()

    @patch.dict("os.environ", {"TAVILY_API_KEY": ""})
    async def test_tavily_search_no_api_key(self):
        """Test Tavily search without API key."""
        service = SearchService(ArticleRepository())
        result = await service.tavily_search("test query")

        assert result["success"] is False
        assert "api key" in result["error"].lower()
        assert result["count"] == 0

    @patch("tavily.TavilyClient")
    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    async def test_tavily_search_success(self, mock_client_class):
        """Test successful Tavily search."""
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "url": "https://techcrunch.com/article1",
                    "title": "AI Breakthrough Announced",
                    "content": "New AI model shows promising results",
                    "source": "TechCrunch",
                    "published_date": "2024-05-18"
                },
                {
                    "url": "https://arxiv.org/paper/2405.12345",
                    "title": "Research Paper on Neural Networks",
                    "content": "Paper abstract about neural networks",
                    "source": "arXiv",
                    "published_date": "2024-05-17"
                }
            ]
        }
        mock_client_class.return_value = mock_client

        service = SearchService(ArticleRepository())
        result = await service.tavily_search("AI breakthroughs", limit=5)

        assert result["success"] is True
        assert result["count"] == 2
        assert result["query"] == "AI breakthroughs"
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "AI Breakthrough Announced"
        assert result["results"][1]["source"] == "arXiv"

    @patch("tavily.TavilyClient")
    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    async def test_tavily_search_empty_results(self, mock_client_class):
        """Test Tavily search with empty results."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        mock_client_class.return_value = mock_client

        service = SearchService(ArticleRepository())
        result = await service.tavily_search("nonexistent query")

        assert result["success"] is True
        assert result["count"] == 0
        assert result["results"] == []

    @patch("tavily.TavilyClient")
    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    async def test_tavily_search_with_custom_domains(self, mock_client_class):
        """Test Tavily search with custom domain filter."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        mock_client_class.return_value = mock_client

        service = SearchService(ArticleRepository())
        custom_domains = ["github.com", "medium.com"]

        await service.tavily_search("test", include_domains=custom_domains)

        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        assert call_args[1]["include_domains"] == custom_domains

    @patch("tavily.TavilyClient")
    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    async def test_tavily_search_api_exception(self, mock_client_class):
        """Test Tavily search with API exception."""
        mock_client_class.side_effect = Exception("API connection failed")

        service = SearchService(ArticleRepository())
        result = await service.tavily_search("test query")

        assert result["success"] is False
        assert "API connection failed" in result["error"]

    @patch("tavily.TavilyClient")
    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    async def test_tavily_search_limit_parameter(self, mock_client_class):
        """Test Tavily search respects limit parameter."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        mock_client_class.return_value = mock_client

        service = SearchService(ArticleRepository())

        await service.tavily_search("test", limit=20)

        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        assert call_args[1]["max_results"] == 20

    @patch("builtins.__import__", side_effect=ImportError)
    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    async def test_tavily_search_library_not_installed(self, mock_import):
        """Test Tavily search when library not installed."""
        service = SearchService(ArticleRepository())
        result = await service.tavily_search("test")

        assert result["success"] is False
        assert "not installed" in result["error"].lower()
