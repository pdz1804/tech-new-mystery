"""Tests for summarization tasks."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.workers.tasks.summary_tasks import _summarize_article, _batch_summarize


@pytest.fixture
def mock_article_repo():
    """Mock article repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_service():
    """Mock summarization service."""
    service = AsyncMock()
    return service


@pytest.fixture
def sample_article():
    """Sample article."""
    article = MagicMock()
    article.article_id = "article-1"
    article.title = "AI Breakthrough in Healthcare"
    article.content = "This article discusses how AI is revolutionizing healthcare..."
    article.category = "Technology"
    article.summary = None
    return article


class TestSummarizeArticle:
    """Tests for _summarize_article function."""

    @pytest.mark.asyncio
    async def test_summarize_article_success(self, sample_article, mock_article_repo):
        """Test successful article summarization."""
        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            mock_article_repo.get_by_id.return_value = sample_article
            mock_service.summarize_article.return_value = (
                "This is a summary about AI in healthcare."
            )
            mock_service.extract_citations.return_value = [
                {"type": "statistic", "text": "AI accuracy: 95%"}
            ]
            mock_service.classify_category.return_value = "Technology"

            result = await _summarize_article("article-1")

            assert result["success"] is True
            assert result["article_id"] == "article-1"
            assert result["title"] == "AI Breakthrough in Healthcare"
            assert result["summary_length"] > 0
            assert result["citations_count"] == 1
            assert result["category"] == "Technology"
            mock_article_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_article_not_found(self, mock_article_repo):
        """Test summarization when article not found."""
        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ):
            mock_article_repo.get_by_id.return_value = None

            result = await _summarize_article("nonexistent")

            assert result["success"] is False
            assert "not found" in result["error"].lower()
            mock_article_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarize_article_already_has_summary(
        self, mock_article_repo
    ):
        """Test skipping article that already has summary."""
        article = MagicMock()
        article.article_id = "article-1"
        article.summary = "Existing summary"

        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ):
            mock_article_repo.get_by_id.return_value = article

            result = await _summarize_article("article-1")

            assert result["success"] is True
            assert result["status"] == "skipped"
            assert "already has summary" in result["reason"].lower()
            mock_article_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarize_article_generation_fails(
        self, sample_article, mock_article_repo
    ):
        """Test handling of failed summary generation."""
        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            mock_article_repo.get_by_id.return_value = sample_article
            mock_service.summarize_article.return_value = None

            result = await _summarize_article("article-1")

            assert result["success"] is False
            assert "failed to generate summary" in result["error"].lower()
            mock_article_repo.update.assert_not_called()


class TestBatchSummarize:
    """Tests for _batch_summarize function."""

    @pytest.mark.asyncio
    async def test_batch_summarize_success(self, sample_article, mock_article_repo):
        """Test successful batch summarization."""
        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Return list with one article
            mock_article_repo.list_all.return_value = ([sample_article], None)
            mock_service.summarize_article.return_value = "Test summary"
            mock_service.extract_citations.return_value = []
            mock_service.classify_category.return_value = "Technology"

            result = await _batch_summarize()

            assert result["total"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            mock_article_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_summarize_no_articles(self, mock_article_repo):
        """Test batch summarization with no articles to process."""
        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ):
            mock_article_repo.list_all.return_value = ([], None)

            result = await _batch_summarize()

            assert result["success"] is True
            assert result["total"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0
            mock_article_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_summarize_mixed_results(self, sample_article, mock_article_repo):
        """Test batch summarization with mixed success/failure."""
        article1 = sample_article
        article2 = MagicMock()
        article2.article_id = "article-2"
        article2.title = "Second Article"
        article2.summary = None
        article2.category = "Science"

        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            mock_article_repo.list_all.return_value = ([article1, article2], None)

            # First succeeds, second fails
            mock_service.summarize_article.side_effect = [
                "Summary 1",
                None,  # Failure
            ]
            mock_service.extract_citations.return_value = []
            mock_service.classify_category.return_value = "Technology"

            result = await _batch_summarize()

            assert result["total"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_batch_summarize_filters_existing_summaries(
        self, mock_article_repo
    ):
        """Test that articles with existing summaries are skipped."""
        article_with_summary = MagicMock()
        article_with_summary.article_id = "article-1"
        article_with_summary.summary = "Existing summary"

        article_without_summary = MagicMock()
        article_without_summary.article_id = "article-2"
        article_without_summary.summary = None

        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            mock_article_repo.list_all.return_value = (
                [article_with_summary, article_without_summary],
                None,
            )
            mock_service.summarize_article.return_value = "New summary"
            mock_service.extract_citations.return_value = []
            mock_service.classify_category.return_value = "Technology"

            result = await _batch_summarize()

            # Only one article should be processed
            assert result["total"] == 1
            assert result["successful"] == 1
            mock_article_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_summarize_updates_category(
        self, sample_article, mock_article_repo
    ):
        """Test that category is updated along with summary."""
        with patch(
            "app.workers.tasks.summary_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.summary_tasks.SummarizationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            mock_article_repo.list_all.return_value = ([sample_article], None)
            mock_service.summarize_article.return_value = "Test summary"
            mock_service.extract_citations.return_value = []
            mock_service.classify_category.return_value = "Science"

            result = await _batch_summarize()

            assert result["successful"] == 1
            # Verify that update was called with category
            call_args = mock_article_repo.update.call_args
            assert "category" in call_args.kwargs
            assert call_args.kwargs["category"] == "Science"
