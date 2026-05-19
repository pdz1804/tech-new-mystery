"""Tests for trending calculation tasks."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.workers.tasks.trending_tasks import (
    _recalculate_trending,
    _calculate_trending_score,
    _get_article_comments_count,
)


@pytest.fixture
def mock_article_repo():
    """Mock article repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_comment_repo():
    """Mock comment repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_trending_repo():
    """Mock trending repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def sample_article():
    """Sample published article."""
    article = MagicMock()
    article.article_id = "article-1"
    article.title = "AI Breakthrough"
    article.is_published = True
    article.view_count = 100
    return article


@pytest.fixture
def sample_article_unpublished():
    """Sample unpublished article."""
    article = MagicMock()
    article.article_id = "article-2"
    article.title = "Draft Article"
    article.is_published = False
    article.view_count = 50
    return article


class TestCalculateTrendingScore:
    """Tests for trending score calculation."""

    @pytest.mark.asyncio
    async def test_calculate_score_basic(self):
        """Test basic score calculation."""
        score = await _calculate_trending_score(
            views=100,
            comments=10,
            saves=5,
        )
        # Expected: (100 * 0.4) + (10 * 0.35) + (5 * 0.25)
        # = 40 + 3.5 + 1.25 = 44.75
        assert score == 44.75

    @pytest.mark.asyncio
    async def test_calculate_score_high_views(self):
        """Test score calculation with high views."""
        score = await _calculate_trending_score(
            views=1000,
            comments=5,
            saves=2,
        )
        # Expected: (1000 * 0.4) + (5 * 0.35) + (2 * 0.25)
        # = 400 + 1.75 + 0.5 = 402.25
        assert score == 402.25

    @pytest.mark.asyncio
    async def test_calculate_score_zeros(self):
        """Test score calculation with zero engagement."""
        score = await _calculate_trending_score(
            views=0,
            comments=0,
            saves=0,
        )
        assert score == 0


class TestGetArticleCommentsCount:
    """Tests for getting article comment counts."""

    @pytest.mark.asyncio
    async def test_get_comments_success(self):
        """Test retrieving comment count."""
        mock_comments = [MagicMock(), MagicMock(), MagicMock()]
        with patch(
            "app.workers.tasks.trending_tasks.CommentRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_article.return_value = mock_comments

            count = await _get_article_comments_count("article-1")

            assert count == 3
            mock_repo.get_by_article.assert_called_once_with("article-1", limit=1000)

    @pytest.mark.asyncio
    async def test_get_comments_empty(self):
        """Test when article has no comments."""
        with patch(
            "app.workers.tasks.trending_tasks.CommentRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_article.return_value = []

            count = await _get_article_comments_count("article-1")

            assert count == 0

    @pytest.mark.asyncio
    async def test_get_comments_error(self):
        """Test error handling for comment retrieval."""
        with patch(
            "app.workers.tasks.trending_tasks.CommentRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_by_article.side_effect = Exception("DB error")

            count = await _get_article_comments_count("article-1")

            assert count == 0


class TestRecalculateTrending:
    """Tests for trending recalculation."""

    @pytest.mark.asyncio
    async def test_recalculate_trending_success(
        self, sample_article, mock_article_repo, mock_trending_repo
    ):
        """Test successful trending calculation."""
        with patch(
            "app.workers.tasks.trending_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.trending_tasks.TrendingRepository",
            return_value=mock_trending_repo,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_comments_count",
            return_value=5,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_saves_count",
            return_value=2,
        ):
            mock_article_repo.list_all.return_value = ([sample_article], None)

            result = await _recalculate_trending()

            assert result["success"] is True
            assert result["total"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0
            assert len(result["articles_ranked"]) == 1
            assert result["articles_ranked"][0]["rank"] == 1
            mock_trending_repo.update_trending_score.assert_called_once()

    @pytest.mark.asyncio
    async def test_recalculate_trending_no_articles(self, mock_article_repo):
        """Test trending calculation with no articles."""
        with patch(
            "app.workers.tasks.trending_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ):
            mock_article_repo.list_all.return_value = ([], None)

            result = await _recalculate_trending()

            assert result["success"] is True
            assert result["total"] == 0
            assert result["successful"] == 0

    @pytest.mark.asyncio
    async def test_recalculate_trending_filters_unpublished(
        self, sample_article, sample_article_unpublished, mock_article_repo, mock_trending_repo
    ):
        """Test that unpublished articles are filtered out."""
        with patch(
            "app.workers.tasks.trending_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.trending_tasks.TrendingRepository",
            return_value=mock_trending_repo,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_comments_count",
            return_value=0,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_saves_count",
            return_value=0,
        ):
            mock_article_repo.list_all.return_value = (
                [sample_article, sample_article_unpublished],
                None,
            )

            result = await _recalculate_trending()

            # Only published article should be processed
            assert result["total"] == 1
            assert result["successful"] == 1
            assert len(result["articles_ranked"]) == 1

    @pytest.mark.asyncio
    async def test_recalculate_trending_multiple_articles_ranked(
        self, mock_article_repo, mock_trending_repo
    ):
        """Test ranking of multiple articles by score."""
        article1 = MagicMock()
        article1.article_id = "article-1"
        article1.title = "High engagement"
        article1.is_published = True
        article1.view_count = 1000

        article2 = MagicMock()
        article2.article_id = "article-2"
        article2.title = "Low engagement"
        article2.is_published = True
        article2.view_count = 10

        with patch(
            "app.workers.tasks.trending_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.trending_tasks.TrendingRepository",
            return_value=mock_trending_repo,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_comments_count",
            return_value=0,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_saves_count",
            return_value=0,
        ):
            mock_article_repo.list_all.return_value = ([article1, article2], None)

            result = await _recalculate_trending()

            assert result["successful"] == 2
            # Article 1 should have rank 1 (higher score)
            assert result["articles_ranked"][0]["article_id"] == "article-1"
            assert result["articles_ranked"][0]["rank"] == 1
            # Article 2 should have rank 2
            assert result["articles_ranked"][1]["article_id"] == "article-2"
            assert result["articles_ranked"][1]["rank"] == 2

    @pytest.mark.asyncio
    async def test_recalculate_trending_article_error(
        self, sample_article, mock_article_repo, mock_trending_repo
    ):
        """Test error handling for individual article processing."""
        with patch(
            "app.workers.tasks.trending_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.trending_tasks.TrendingRepository",
            return_value=mock_trending_repo,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_comments_count",
            side_effect=Exception("DB error"),
        ):
            mock_article_repo.list_all.return_value = ([sample_article], None)

            result = await _recalculate_trending()

            assert result["total"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_recalculate_trending_save_error(
        self, sample_article, mock_article_repo, mock_trending_repo
    ):
        """Test error handling when saving trending records."""
        with patch(
            "app.workers.tasks.trending_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.trending_tasks.TrendingRepository",
            return_value=mock_trending_repo,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_comments_count",
            return_value=0,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_saves_count",
            return_value=0,
        ):
            mock_article_repo.list_all.return_value = ([sample_article], None)
            mock_trending_repo.update_trending_score.side_effect = Exception("Save failed")

            result = await _recalculate_trending()

            assert result["success"] is True
            assert result["successful"] == 1
            assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_recalculate_trending_top_50_limit(self, mock_article_repo, mock_trending_repo):
        """Test that only top 50 articles are ranked."""
        articles = []
        for i in range(100):
            article = MagicMock()
            article.article_id = f"article-{i}"
            article.title = f"Article {i}"
            article.is_published = True
            article.view_count = 100 - i  # Decreasing views
            articles.append(article)

        with patch(
            "app.workers.tasks.trending_tasks.ArticleRepository",
            return_value=mock_article_repo,
        ), patch(
            "app.workers.tasks.trending_tasks.TrendingRepository",
            return_value=mock_trending_repo,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_comments_count",
            return_value=0,
        ), patch(
            "app.workers.tasks.trending_tasks._get_article_saves_count",
            return_value=0,
        ):
            mock_article_repo.list_all.return_value = (articles, None)

            result = await _recalculate_trending()

            assert result["total"] == 100
            assert result["successful"] == 100
            # Only top 50 should be ranked
            assert len(result["articles_ranked"]) == 50
            # Check ranking order
            for i, ranked in enumerate(result["articles_ranked"], start=1):
                assert ranked["rank"] == i
