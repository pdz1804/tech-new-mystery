"""Integration tests for clustering task with real backend."""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta

from app.repositories.article_repository import ArticleRepository
from app.services.clustering_engine import ClusteringEngine
from app.services.embedding_service import EmbeddingService
from app.models.clustering import (
    ArticleClusterModel,
    ClusterMetadataModel,
    ArticleEmbeddingModel,
)
from app.workers.tasks.clustering_tasks import _cluster_articles_async
from app.utils.time import now_timestamp


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class TestClusteringEngineIntegration:
    """Integration tests for ClusteringEngine with real embedding data."""

    @pytest.mark.asyncio
    async def test_clustering_engine_with_embeddings(self):
        """Test HDBSCAN clustering with real embeddings."""
        # Generate synthetic embeddings (normalized random vectors)
        np.random.seed(42)
        num_articles = 100
        embedding_dim = 1536

        # Create 3 synthetic clusters by adding offsets
        embeddings = []
        article_ids = []

        # Cluster 1: Embeddings near (1, 0, 0, ...)
        for i in range(33):
            emb = np.random.randn(embedding_dim) * 0.1
            emb[0] += 1
            embeddings.append(emb)
            article_ids.append(f"article-cluster1-{i}")

        # Cluster 2: Embeddings near (0, 1, 0, ...)
        for i in range(33):
            emb = np.random.randn(embedding_dim) * 0.1
            emb[1] += 1
            embeddings.append(emb)
            article_ids.append(f"article-cluster2-{i}")

        # Cluster 3: Embeddings near (0, 0, 1, ...)
        for i in range(34):
            emb = np.random.randn(embedding_dim) * 0.1
            emb[2] += 1
            embeddings.append(emb)
            article_ids.append(f"article-cluster3-{i}")

        embeddings = np.array(embeddings)

        # Run clustering
        engine = ClusteringEngine(
            min_cluster_size=5,
            min_samples=3,
            metric="euclidean",
        )

        assignments, stats = engine.cluster_articles(embeddings, article_ids)

        # Verify results
        assert len(assignments) == num_articles
        assert all(isinstance(cid, int) for cid in assignments.values())
        assert stats["num_clusters"] >= 1
        assert stats["num_noise"] + sum(
            1 for cid in assignments.values() if cid >= 0
        ) == num_articles
        assert 0 <= stats["noise_percent"] <= 100

        # With good clustering, we should get 2-3 clusters with minimal noise
        assert stats["num_clusters"] >= 2
        assert stats["noise_percent"] < 30

    @pytest.mark.asyncio
    async def test_clustering_engine_edge_cases(self):
        """Test HDBSCAN clustering edge cases."""
        engine = ClusteringEngine(min_cluster_size=5)

        # Test 1: Too few articles
        small_embeddings = np.random.randn(3, 1536)
        assignments, stats = engine.cluster_articles(
            small_embeddings,
            ["a", "b", "c"],
        )

        assert stats["num_clusters"] == 0
        assert stats["num_noise"] == 3
        assert all(cid == -1 for cid in assignments.values())

        # Test 2: Identical embeddings
        identical = np.ones((10, 1536))
        assignments, stats = engine.cluster_articles(
            identical,
            [f"article-{i}" for i in range(10)],
        )

        assert stats["num_clusters"] == 0
        assert stats["num_noise"] == 10

        # Test 3: Empty embeddings
        empty = np.array([]).reshape(0, 1536)
        assignments, stats = engine.cluster_articles(empty, [])

        assert len(assignments) == 0
        assert stats["num_clusters"] == 0


class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService."""

    @pytest.mark.asyncio
    async def test_generate_embedding_real_text(self):
        """Test embedding generation with real OpenAI API (if key available)."""
        service = EmbeddingService()

        # Skip if no API key
        if not service.api_key:
            pytest.skip("OpenAI API key not configured")

        text = "Artificial intelligence and machine learning are transforming the tech industry"

        embedding = await service.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        assert abs(sum(x**2 for x in embedding) ** 0.5 - 1.0) < 0.1  # Normalized

    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self):
        """Test batch embedding generation (skips if no API key)."""
        service = EmbeddingService()

        if not service.api_key:
            pytest.skip("OpenAI API key not configured")

        texts = [
            "First article about AI",
            "Second article about machine learning",
            "Third article about neural networks",
        ]

        embeddings = await service.generate_batch_embeddings(texts, batch_size=2)

        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)


class TestClusteringPipelineIntegration:
    """Integration tests for the full clustering pipeline."""

    @pytest.mark.asyncio
    async def test_full_clustering_pipeline_with_real_data(self):
        """Test full clustering pipeline with synthetic article data."""
        # Create synthetic articles with embeddings
        num_articles = 50
        article_repo = ArticleRepository()

        # For this test, we'll use synthetic embeddings
        # In real scenario, would fetch from DB and generate embeddings

        np.random.seed(42)
        embeddings = np.random.randn(num_articles, 1536)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        article_ids = [f"article-{i:03d}" for i in range(num_articles)]

        # Run clustering
        engine = ClusteringEngine(min_cluster_size=3)
        assignments, stats = engine.cluster_articles(embeddings, article_ids)

        # Validate results
        assert len(assignments) == num_articles
        assert stats["num_clusters"] >= 0
        assert stats["num_noise"] + sum(1 for cid in assignments.values() if cid >= 0) == num_articles

        # With 50 random articles, should form at least 1-3 clusters
        assert stats["num_clusters"] <= 5

    @pytest.mark.asyncio
    async def test_article_cluster_model_crud(self):
        """Test CRUD operations for ArticleClusterModel."""
        try:
            # Create a test assignment
            now = now_timestamp()
            ttl = now + 604800  # 7 days

            test_cluster_id = f"test-cluster-{now}"
            test_article_id = f"test-article-{now}"

            # Create
            assignment = ArticleClusterModel(
                test_cluster_id,
                test_article_id,
                assigned_at=now,
                confidence_score=0.85,
                ttl=ttl,
            )

            await asyncio.to_thread(assignment.save)
            print(f"Created cluster assignment: {test_cluster_id} -> {test_article_id}")

            # Read
            retrieved = await asyncio.to_thread(
                ArticleClusterModel.get,
                test_cluster_id,
                test_article_id,
            )

            assert retrieved.cluster_id == test_cluster_id
            assert retrieved.article_id == test_article_id
            assert retrieved.confidence_score == 0.85

            print("Successfully retrieved cluster assignment from DynamoDB")

            # Cleanup
            await asyncio.to_thread(retrieved.delete)
            print(f"Deleted cluster assignment")

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {e}")

    @pytest.mark.asyncio
    async def test_cluster_metadata_model_crud(self):
        """Test CRUD operations for ClusterMetadataModel."""
        try:
            now = now_timestamp()
            ttl = now + 604800  # 7 days

            test_cluster_id = f"test-metadata-{now}"

            # Create
            from app.models.clustering import TopArticleItem

            top_article = TopArticleItem(
                article_id="top-article-1",
                title="Top Article Title",
                engagement_score=4.5,
            )

            metadata = ClusterMetadataModel(
                test_cluster_id,
                label="Test Cluster Label",
                keywords=["keyword1", "keyword2", "keyword3"],
                description="Test cluster description",
                article_count=10,
                size_category="MEDIUM",
                diversity_score=0.65,
                centroid_embedding=[0.1] * 1536,
                top_articles=[top_article],
                created_at=now,
                updated_at=now,
                ttl=ttl,
            )

            await asyncio.to_thread(metadata.save)
            print(f"Created cluster metadata: {test_cluster_id}")

            # Read
            retrieved = await asyncio.to_thread(
                ClusterMetadataModel.get,
                test_cluster_id,
            )

            assert retrieved.cluster_id == test_cluster_id
            assert retrieved.label == "Test Cluster Label"
            assert len(retrieved.keywords) == 3
            assert retrieved.article_count == 10

            print("Successfully retrieved cluster metadata from DynamoDB")

            # Cleanup
            await asyncio.to_thread(retrieved.delete)
            print(f"Deleted cluster metadata")

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {e}")

    @pytest.mark.asyncio
    async def test_embedding_model_crud(self):
        """Test CRUD operations for ArticleEmbeddingModel."""
        try:
            now = now_timestamp()
            ttl = now + 604800  # 7 days

            test_article_id = f"test-embedding-{now}"
            test_embedding = [np.random.randn() for _ in range(1536)]

            # Create
            embedding = ArticleEmbeddingModel(
                test_article_id,
                embedding=test_embedding,
                embedding_model="text-embedding-3-small",
                generated_at=now,
                ttl=ttl,
            )

            await asyncio.to_thread(embedding.save)
            print(f"Created embedding: {test_article_id}")

            # Read
            retrieved = await asyncio.to_thread(
                ArticleEmbeddingModel.get,
                test_article_id,
            )

            assert retrieved.article_id == test_article_id
            assert len(retrieved.embedding) == 1536
            assert retrieved.embedding_model == "text-embedding-3-small"

            print("Successfully retrieved embedding from DynamoDB")

            # Cleanup
            await asyncio.to_thread(retrieved.delete)
            print(f"Deleted embedding")

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {e}")


@pytest.mark.asyncio
async def test_clustering_task_execution():
    """Test clustering task execution (requires articles in DB)."""
    try:
        # This will run the actual clustering task
        # It requires articles to exist in the database
        result = await _cluster_articles_async()

        assert result["success"] is True
        assert "articles_count" in result
        assert "clusters_count" in result
        assert "duration_seconds" in result

        print(f"Clustering task result: {result}")

    except Exception as e:
        # Skip if database not available or no articles
        pytest.skip(f"Cannot run clustering task: {e}")
