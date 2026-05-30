"""Unit tests for clustering tasks."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from app.workers.tasks.clustering_tasks import (
    _cluster_articles_async,
    _get_or_generate_embeddings,
    _save_clustering_results,
    _calculate_confidence_score,
    _generate_and_save_cluster_metadata,
    _extract_keywords_tfidf,
    _generate_cluster_label,
    _generate_cluster_description,
    _calculate_diversity_score,
    _calculate_centroid_embedding,
    _get_top_articles,
)


@pytest.fixture
def sample_articles():
    """Sample articles for testing."""
    articles = []
    for i in range(10):
        article = MagicMock()
        article.article_id = f"article-{i}"
        article.title = f"Test Article {i}: AI and Technology"
        article.summary = f"This article discusses AI, machine learning, and technology trends."
        article.content = f"Content for article {i}..."
        article.engagement_score = float(i)
        article.quality_score = float(i) / 10
        articles.append(article)
    return articles


@pytest.fixture
def sample_embeddings():
    """Generate sample 1536-dimensional embeddings."""
    np.random.seed(42)
    embeddings = np.random.randn(10, 1536).astype(np.float32)
    # Normalize embeddings
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings


@pytest.fixture
def sample_cluster_assignments():
    """Sample cluster assignments."""
    return {
        "article-0": 0,
        "article-1": 0,
        "article-2": 0,
        "article-3": 1,
        "article-4": 1,
        "article-5": 1,
        "article-6": -1,  # Noise
        "article-7": -1,  # Noise
        "article-8": 2,
        "article-9": 2,
    }


@pytest.fixture
def sample_stats():
    """Sample clustering statistics."""
    return {
        "num_clusters": 3,
        "num_noise": 2,
        "noise_percent": 20.0,
        "avg_cluster_size": 2.67,
        "cluster_sizes": {"0": 3, "1": 3, "-1": 2, "2": 2},
    }


class TestGetOrGenerateEmbeddings:
    """Tests for _get_or_generate_embeddings function."""

    @pytest.mark.asyncio
    async def test_get_cached_embeddings(self, sample_articles, sample_embeddings):
        """Test retrieving cached embeddings."""
        embedding_service = AsyncMock()

        with patch(
            "app.workers.tasks.clustering_tasks.ArticleEmbeddingModel"
        ) as mock_model:
            # Mock cached embeddings
            mock_embedding = MagicMock()
            mock_embedding.embedding = sample_embeddings[0].tolist()

            mock_model.get.return_value = mock_embedding

            embeddings, article_ids = await _get_or_generate_embeddings(
                sample_articles, embedding_service
            )

            # Should have retrieved cached embeddings
            assert len(embeddings) > 0
            assert len(article_ids) == len(embeddings)

    @pytest.mark.asyncio
    async def test_generate_missing_embeddings(self, sample_articles, sample_embeddings):
        """Test generating embeddings for articles not in cache."""
        embedding_service = AsyncMock()
        embedding_service.generate_embedding.return_value = sample_embeddings[0].tolist()

        with patch(
            "app.workers.tasks.clustering_tasks.ArticleEmbeddingModel"
        ) as mock_model:
            # Mock: all embeddings not cached
            mock_model.get.side_effect = Exception("Not found")

            embeddings, article_ids = await _get_or_generate_embeddings(
                sample_articles[:3], embedding_service
            )

            # Should have generated embeddings
            assert len(embeddings) > 0
            assert embedding_service.generate_embedding.called

    @pytest.mark.asyncio
    async def test_empty_articles_list(self):
        """Test with empty articles list."""
        embedding_service = AsyncMock()

        embeddings, article_ids = await _get_or_generate_embeddings(
            [], embedding_service
        )

        assert len(embeddings) == 0
        assert len(article_ids) == 0


class TestCalculateConfidenceScore:
    """Tests for _calculate_confidence_score function."""

    def test_calculate_confidence_single_article(self, sample_embeddings, sample_cluster_assignments):
        """Test confidence calculation for a single article."""
        article_idx = 0
        article_embedding = sample_embeddings[article_idx]

        confidence = _calculate_confidence_score(
            article_embedding,
            sample_embeddings,
            sample_cluster_assignments,
            cluster_id=0,
        )

        # Confidence should be between 0 and 1
        assert 0.0 <= confidence <= 1.0

    def test_confidence_empty_cluster(self, sample_embeddings):
        """Test confidence calculation with empty cluster."""
        article_embedding = sample_embeddings[0]
        empty_assignments = {"article-0": 0}  # No cluster 1

        confidence = _calculate_confidence_score(
            article_embedding,
            sample_embeddings,
            empty_assignments,
            cluster_id=1,  # Non-existent
        )

        assert confidence == 0.0


class TestExtractKeywordsTfidf:
    """Tests for _extract_keywords_tfidf function."""

    @pytest.mark.asyncio
    async def test_extract_keywords_from_articles(self, sample_articles):
        """Test keyword extraction from articles."""
        keywords = await _extract_keywords_tfidf(sample_articles)

        assert len(keywords) == 5
        assert all(isinstance(k, str) for k in keywords)
        assert all(len(k) > 0 for k in keywords)

    @pytest.mark.asyncio
    async def test_extract_keywords_empty_articles(self):
        """Test keyword extraction with empty articles."""
        keywords = await _extract_keywords_tfidf([])

        # Should return fallback keywords
        assert len(keywords) == 5


class TestGenerateClusterLabel:
    """Tests for _generate_cluster_label function."""

    @pytest.mark.asyncio
    async def test_generate_label_success(self, sample_articles):
        """Test successful label generation."""
        keywords = ["AI", "Technology", "Innovation"]

        with patch("app.integrations.llm_client.get_llm_client") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            mock_llm.generate.return_value = "AI & Technology Innovation"

            label = await _generate_cluster_label(keywords, sample_articles)

            assert isinstance(label, str)
            assert len(label) > 0
            assert len(label) <= 100

    @pytest.mark.asyncio
    async def test_generate_label_fallback(self, sample_articles):
        """Test label generation fallback on error."""
        keywords = ["AI", "Tech", "News"]

        with patch("app.integrations.llm_client.get_llm_client") as mock_get_llm:
            mock_get_llm.side_effect = Exception("API error")

            label = await _generate_cluster_label(keywords, sample_articles)

            # Should fallback to keyword combination
            assert "AI" in label or "Tech" in label


class TestGenerateClusterDescription:
    """Tests for _generate_cluster_description function."""

    @pytest.mark.asyncio
    async def test_generate_description_success(self, sample_articles):
        """Test successful description generation."""
        keywords = ["AI", "Technology"]
        label = "AI & Technology"

        with patch("app.integrations.llm_client.get_llm_client") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            mock_llm.generate.return_value = "Latest developments in artificial intelligence and tech"

            description = await _generate_cluster_description(label, keywords, sample_articles)

            assert isinstance(description, str)
            assert len(description) > 0
            assert len(description) <= 500

    @pytest.mark.asyncio
    async def test_generate_description_fallback(self, sample_articles):
        """Test description fallback on error."""
        with patch("app.integrations.llm_client.get_llm_client") as mock_get_llm:
            mock_get_llm.side_effect = Exception("API error")

            description = await _generate_cluster_description(
                "AI", ["AI"], sample_articles
            )

            # Should have fallback text
            assert "Collection of articles" in description


class TestCalculateDiversityScore:
    """Tests for _calculate_diversity_score function."""

    @pytest.mark.asyncio
    async def test_calculate_diversity_multiple_articles(self, sample_embeddings):
        """Test diversity calculation with multiple articles."""
        article_ids = ["article-0", "article-1", "article-2"]
        all_article_ids = [f"article-{i}" for i in range(10)]

        diversity = await _calculate_diversity_score(
            article_ids,
            sample_embeddings,
            all_article_ids,
        )

        assert 0.0 <= diversity <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_diversity_single_article(self, sample_embeddings):
        """Test diversity calculation with single article."""
        article_ids = ["article-0"]
        all_article_ids = [f"article-{i}" for i in range(10)]

        diversity = await _calculate_diversity_score(
            article_ids,
            sample_embeddings,
            all_article_ids,
        )

        # Single article should have default diversity
        assert diversity == 0.5


class TestCalculateCentroidEmbedding:
    """Tests for _calculate_centroid_embedding function."""

    @pytest.mark.asyncio
    async def test_calculate_centroid(self, sample_embeddings):
        """Test centroid embedding calculation."""
        article_ids = ["article-0", "article-1", "article-2"]
        all_article_ids = [f"article-{i}" for i in range(10)]

        centroid = await _calculate_centroid_embedding(
            article_ids,
            sample_embeddings,
            all_article_ids,
        )

        assert len(centroid) == 1536
        assert all(isinstance(x, float) for x in centroid)

    @pytest.mark.asyncio
    async def test_calculate_centroid_empty(self, sample_embeddings):
        """Test centroid calculation with empty articles."""
        all_article_ids = [f"article-{i}" for i in range(10)]

        centroid = await _calculate_centroid_embedding(
            [],
            sample_embeddings,
            all_article_ids,
        )

        # Should return zero vector
        assert len(centroid) == 1536
        assert all(x == 0.0 for x in centroid)


class TestGetTopArticles:
    """Tests for _get_top_articles function."""

    @pytest.mark.asyncio
    async def test_get_top_articles(self, sample_articles):
        """Test getting top articles by engagement."""
        top_articles = await _get_top_articles(sample_articles, limit=5)

        assert len(top_articles) <= 5
        assert len(top_articles) > 0

    @pytest.mark.asyncio
    async def test_get_top_articles_empty(self):
        """Test getting top articles from empty list."""
        top_articles = await _get_top_articles([], limit=5)

        assert len(top_articles) == 0


class TestSaveClusteringResults:
    """Tests for _save_clustering_results function."""

    @pytest.mark.asyncio
    async def test_save_clustering_results(
        self,
        sample_articles,
        sample_embeddings,
        sample_cluster_assignments,
        sample_stats,
    ):
        """Test saving clustering results to DynamoDB."""
        article_repo = AsyncMock()
        article_ids = [f"article-{i}" for i in range(10)]

        with patch(
            "app.workers.tasks.clustering_tasks.ArticleClusterModel"
        ) as mock_cluster_model, patch(
            "app.workers.tasks.clustering_tasks._generate_and_save_cluster_metadata"
        ) as mock_gen_metadata:

            mock_cluster_instance = MagicMock()
            mock_cluster_model.return_value = mock_cluster_instance

            saved_count = await _save_clustering_results(
                sample_cluster_assignments,
                sample_stats,
                sample_embeddings,
                article_ids,
                sample_articles,
                article_repo,
            )

            # Should have saved assignments (excluding noise)
            assert saved_count > 0

    @pytest.mark.asyncio
    async def test_save_clustering_results_empty(self, sample_embeddings, sample_stats):
        """Test saving with empty cluster assignments."""
        article_repo = AsyncMock()
        article_ids = [f"article-{i}" for i in range(10)]

        saved_count = await _save_clustering_results(
            {},  # Empty assignments
            sample_stats,
            sample_embeddings,
            article_ids,
            [],  # Empty articles
            article_repo,
        )

        assert saved_count == 0


class TestClusterArticlesAsync:
    """Tests for _cluster_articles_async function."""

    @pytest.mark.asyncio
    async def test_cluster_articles_success(self, sample_articles, sample_embeddings):
        """Test successful clustering pipeline."""
        article_repo = AsyncMock()
        article_repo.list_all.return_value = (sample_articles, None)

        with patch(
            "app.workers.tasks.clustering_tasks.ArticleRepository",
            return_value=article_repo,
        ), patch(
            "app.workers.tasks.clustering_tasks._get_or_generate_embeddings"
        ) as mock_get_embeddings, patch(
            "app.workers.tasks.clustering_tasks.ClusteringEngine"
        ) as mock_engine_class, patch(
            "app.workers.tasks.clustering_tasks._save_clustering_results"
        ) as mock_save:

            article_ids = [f"article-{i}" for i in range(10)]
            mock_get_embeddings.return_value = (
                sample_embeddings.tolist(),
                article_ids,
            )

            mock_engine = MagicMock()
            mock_engine_class.return_value = mock_engine
            mock_engine.cluster_articles.return_value = (
                {aid: i % 2 for i, aid in enumerate(article_ids)},
                {"num_clusters": 2, "num_noise": 0, "noise_percent": 0.0},
            )

            mock_save.return_value = 10

            result = await _cluster_articles_async()

            assert result["success"] is True
            assert result["clusters_count"] == 2
            assert result["articles_count"] == 10

    @pytest.mark.asyncio
    async def test_cluster_articles_no_articles(self):
        """Test clustering with no articles."""
        article_repo = AsyncMock()
        article_repo.list_all.return_value = ([], None)

        with patch(
            "app.workers.tasks.clustering_tasks.ArticleRepository",
            return_value=article_repo,
        ):
            result = await _cluster_articles_async()

            assert result["success"] is True
            assert result["articles_count"] == 0
            assert result["clusters_count"] == 0

    @pytest.mark.asyncio
    async def test_cluster_articles_no_embeddings(self, sample_articles):
        """Test clustering with failed embeddings."""
        article_repo = AsyncMock()
        article_repo.list_all.return_value = (sample_articles, None)

        with patch(
            "app.workers.tasks.clustering_tasks.ArticleRepository",
            return_value=article_repo,
        ), patch(
            "app.workers.tasks.clustering_tasks._get_or_generate_embeddings"
        ) as mock_get_embeddings:
            # Return empty embeddings
            mock_get_embeddings.return_value = ([], [])

            result = await _cluster_articles_async()

            assert result["success"] is True
            assert result["clusters_count"] == 0
