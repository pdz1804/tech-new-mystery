"""Tests for article summarization service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.summarization_service import SummarizationService
from app.repositories.article_repository import ArticleRepository


class MockArticle:
    """Mock article for testing."""

    def __init__(self, article_id, title, content, summary=None):
        self.id = article_id
        self.title = title
        self.content = content
        self.summary = summary


class TestSummarizationService:
    """Tests for summarization service."""

    @pytest.fixture
    def mock_article_repo(self):
        """Create mock article repository."""
        repo = MagicMock(spec=ArticleRepository)
        return repo

    @pytest.fixture
    def service(self, mock_article_repo):
        """Create summarization service."""
        return SummarizationService(mock_article_repo)

    @pytest.mark.asyncio
    async def test_summarize_article_success(self, service, mock_article_repo):
        """Test successful article summarization."""
        article = MockArticle(
            "art-1",
            "AI Breakthroughs",
            "Long article content about AI advancement and future implications...",
        )
        mock_article_repo.get = AsyncMock(return_value=article)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="AI advancements show promise for future applications."
            )
            mock_llm.return_value = mock_client

            result = await service.summarize_article("art-1")

            assert result is not None
            assert "AI advancements" in result
            assert mock_article_repo.get.called

    @pytest.mark.asyncio
    async def test_summarize_article_not_found(self, service, mock_article_repo):
        """Test summarization when article not found."""
        mock_article_repo.get = AsyncMock(return_value=None)

        result = await service.summarize_article("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_summarize_article_no_content(self, service, mock_article_repo):
        """Test summarization when article has no content."""
        article = MockArticle("art-1", "Title Only", "")
        mock_article_repo.get = AsyncMock(return_value=article)

        result = await service.summarize_article("art-1")

        assert result is None

    @pytest.mark.asyncio
    async def test_summarize_article_long_content_truncation(
        self, service, mock_article_repo
    ):
        """Test that long content is truncated."""
        long_content = "x" * 5000
        article = MockArticle("art-1", "Long Article", long_content)
        mock_article_repo.get = AsyncMock(return_value=article)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Summary")
            mock_llm.return_value = mock_client

            await service.summarize_article("art-1")

            # Verify that generate was called with truncated content
            call_args = mock_client.generate.call_args
            assert "..." in call_args[1]["prompt"]

    @pytest.mark.asyncio
    async def test_extract_citations_success(self, service, mock_article_repo):
        """Test successful citation extraction."""
        article = MockArticle("art-1", "Research Article", "Content with citations...")
        mock_article_repo.get = AsyncMock(return_value=article)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value='[{"type": "citation", "text": "Study shows...", "source": "Journal"}]'
            )
            mock_llm.return_value = mock_client

            citations = await service.extract_citations("art-1", "Summary")

            assert isinstance(citations, list)
            assert len(citations) > 0

    @pytest.mark.asyncio
    async def test_extract_citations_invalid_json(self, service, mock_article_repo):
        """Test citation extraction with invalid JSON response."""
        article = MockArticle("art-1", "Article", "Content...")
        mock_article_repo.get = AsyncMock(return_value=article)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Invalid JSON response")
            mock_llm.return_value = mock_client

            citations = await service.extract_citations("art-1", "Summary")

            assert citations == []

    @pytest.mark.asyncio
    async def test_classify_category_success(self, service, mock_article_repo):
        """Test successful category classification."""
        article = MockArticle("art-1", "Tech Article", "About technology...")
        mock_article_repo.get = AsyncMock(return_value=article)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Technology")
            mock_llm.return_value = mock_client

            category = await service.classify_category("art-1")

            assert category == "Technology"

    @pytest.mark.asyncio
    async def test_classify_category_invalid_response(self, service, mock_article_repo):
        """Test category classification with invalid response."""
        article = MockArticle("art-1", "Article", "Content...")
        mock_article_repo.get = AsyncMock(return_value=article)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Invalid Category")
            mock_llm.return_value = mock_client

            category = await service.classify_category("art-1")

            # Should return default category when response doesn't match
            assert category == "Technology"  # First category in list

    @pytest.mark.asyncio
    async def test_batch_summarize(self, service, mock_article_repo):
        """Test batch summarization."""
        articles = [
            MockArticle("art-1", "Article 1", "Content 1"),
            MockArticle("art-2", "Article 2", "Content 2"),
            MockArticle("art-3", "Article 3", "Content 3"),
        ]
        mock_article_repo.get = AsyncMock(side_effect=articles)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                side_effect=["Summary 1", "Summary 2", "Summary 3"]
            )
            mock_llm.return_value = mock_client

            results = await service.batch_summarize(
                ["art-1", "art-2", "art-3"], batch_size=2
            )

            assert len(results) == 3
            assert "art-1" in results
            assert results["art-1"] == "Summary 1"

    @pytest.mark.asyncio
    async def test_summarize_article_with_custom_parameters(
        self, service, mock_article_repo
    ):
        """Test summarization with custom max_tokens and temperature."""
        article = MockArticle("art-1", "Title", "Content...")
        mock_article_repo.get = AsyncMock(return_value=article)

        with patch("app.services.summarization_service.get_llm_client") as mock_llm:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Summary")
            mock_llm.return_value = mock_client

            await service.summarize_article("art-1", max_tokens=500, temperature=0.8)

            # Verify custom parameters were passed
            call_kwargs = mock_client.generate.call_args[1]
            assert call_kwargs["max_tokens"] == 500
            assert call_kwargs["temperature"] == 0.8
