"""Integration tests for cluster API endpoints with real DynamoDB."""

import pytest
import asyncio
from datetime import datetime

from app.repositories.cluster_repository import ClusterRepository
from app.models.clustering import (
    ArticleClusterModel,
    ClusterMetadataModel,
    TopArticleItem,
)
from app.models.article import ArticleModel
from app.utils.time import now_timestamp


@pytest.fixture
async def setup_test_data():
    """Setup test data in DynamoDB.

    Creates a test cluster with articles for integration testing.
    """
    # Generate unique IDs for this test run
    import time
    test_id = str(int(time.time() * 1000))

    cluster_id = f"test-cluster-{test_id}"
    article_ids = [f"test-article-{test_id}-{i}" for i in range(15)]

    # Create test articles
    articles_to_save = []
    for i, article_id in enumerate(article_ids):
        article = ArticleModel(
            article_id=article_id,
            title=f"Test Article {i}",
            slug=f"test-article-{i}",
            source_id="test-source",
            original_url=f"https://example.com/article-{i}",
            summary=f"Test summary {i}",
            published_at=now_timestamp() - (i * 3600),
            view_count=100 + i * 10,
            created_at=now_timestamp(),
            updated_at=now_timestamp(),
        )
        articles_to_save.append(article)

    # Save articles in batch
    for article in articles_to_save:
        await asyncio.to_thread(article.save)

    # Create test cluster metadata
    top_articles = [
        TopArticleItem(
            article_id=article_ids[0],
            title="Test Article 0",
            engagement_score=4.5,
        ),
        TopArticleItem(
            article_id=article_ids[1],
            title="Test Article 1",
            engagement_score=4.2,
        ),
    ]

    cluster = ClusterMetadataModel(
        cluster_id=cluster_id,
        label="Test Cluster Label",
        description="Test cluster description",
        article_count=len(article_ids),
        size_category="MEDIUM",
        diversity_score=0.45,
        keywords=["test", "keyword1", "keyword2", "keyword3", "keyword4"],
        centroid_embedding=[0.1] * 1536,
        top_articles=top_articles,
        created_at=now_timestamp(),
        updated_at=now_timestamp(),
        ttl=now_timestamp() + (7 * 86400),  # 7 days TTL
    )
    await asyncio.to_thread(cluster.save)

    # Create cluster assignments
    for i, article_id in enumerate(article_ids):
        assignment = ArticleClusterModel(
            cluster_id=cluster_id,
            article_id=article_id,
            confidence_score=0.8 + (i * 0.01),
            assigned_at=now_timestamp(),
            ttl=now_timestamp() + (7 * 86400),
        )
        await asyncio.to_thread(assignment.save)

    yield {
        "cluster_id": cluster_id,
        "article_ids": article_ids,
    }

    # Cleanup: delete test data
    try:
        await asyncio.to_thread(cluster.delete)
        for article_id in article_ids:
            for assignment in ArticleClusterModel.query(cluster_id):
                await asyncio.to_thread(assignment.delete)
            article = await asyncio.to_thread(ArticleModel.get, article_id)
            await asyncio.to_thread(article.delete)
    except Exception as e:
        print(f"Cleanup error: {e}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_cluster_metadata(setup_test_data):
    """Test retrieving cluster metadata from DynamoDB."""
    data = await setup_test_data
    cluster_id = data["cluster_id"]

    repo = ClusterRepository()
    cluster = await repo.get_cluster_metadata(cluster_id)

    assert cluster is not None
    assert cluster.cluster_id == cluster_id
    assert cluster.label == "Test Cluster Label"
    assert cluster.article_count == 15
    assert cluster.size_category == "MEDIUM"
    assert len(cluster.keywords) == 5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_articles_in_cluster(setup_test_data):
    """Test retrieving articles in a cluster."""
    data = await setup_test_data
    cluster_id = data["cluster_id"]

    repo = ClusterRepository()
    articles, next_key = await repo.get_articles_in_cluster(cluster_id, limit=10)

    assert len(articles) == 10
    assert articles[0].cluster_id == cluster_id
    assert articles[0].article_id in data["article_ids"]
    assert 0 <= articles[0].confidence_score <= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_articles_in_cluster_pagination(setup_test_data):
    """Test pagination when fetching articles in cluster."""
    data = await setup_test_data
    cluster_id = data["cluster_id"]

    repo = ClusterRepository()

    # Fetch first page
    articles_page1, next_key = await repo.get_articles_in_cluster(
        cluster_id, limit=5
    )

    assert len(articles_page1) == 5
    assert next_key is not None

    # Fetch second page
    articles_page2, next_key2 = await repo.get_articles_in_cluster(
        cluster_id, limit=5, last_key=next_key
    )

    assert len(articles_page2) <= 5
    assert articles_page1[0].article_id != articles_page2[0].article_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_article_cluster_assignment(setup_test_data):
    """Test retrieving cluster assignment for an article."""
    data = await setup_test_data
    article_id = data["article_ids"][0]

    repo = ClusterRepository()
    assignment = await repo.get_article_cluster_assignment(article_id)

    assert assignment is not None
    assert assignment.article_id == article_id
    assert assignment.cluster_id == data["cluster_id"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_articles_by_ids(setup_test_data):
    """Test batch fetching articles by ID."""
    data = await setup_test_data
    article_ids = data["article_ids"][:5]

    repo = ClusterRepository()
    articles = await repo.get_articles_by_ids(article_ids)

    assert len(articles) == 5
    assert all(a.article_id in article_ids for a in articles)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_count_clusters(setup_test_data):
    """Test counting clusters."""
    await setup_test_data  # Ensure test data exists

    repo = ClusterRepository()
    count = await repo.count_clusters()

    # Should have at least 1 (the test cluster)
    assert count >= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_cluster_metadata(setup_test_data):
    """Test listing cluster metadata."""
    await setup_test_data

    repo = ClusterRepository()
    clusters, next_key = await repo.list_cluster_metadata(limit=10)

    assert len(clusters) > 0
    assert all(hasattr(c, 'cluster_id') for c in clusters)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_cluster_metadata_sorting(setup_test_data):
    """Test sorting when listing clusters."""
    await setup_test_data

    repo = ClusterRepository()

    # Test sort by size
    clusters_by_size, _ = await repo.list_cluster_metadata(limit=100, sort_by="size")
    if len(clusters_by_size) > 1:
        for i in range(len(clusters_by_size) - 1):
            assert (
                clusters_by_size[i].article_count
                >= clusters_by_size[i + 1].article_count
            )

    # Test sort by recency
    clusters_by_recency, _ = await repo.list_cluster_metadata(
        limit=100, sort_by="recency"
    )
    if len(clusters_by_recency) > 1:
        for i in range(len(clusters_by_recency) - 1):
            assert clusters_by_recency[i].updated_at >= clusters_by_recency[i + 1].updated_at

    # Test sort by diversity
    clusters_by_diversity, _ = await repo.list_cluster_metadata(
        limit=100, sort_by="diversity"
    )
    if len(clusters_by_diversity) > 1:
        for i in range(len(clusters_by_diversity) - 1):
            assert (
                clusters_by_diversity[i].diversity_score
                >= clusters_by_diversity[i + 1].diversity_score
            )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_trending_clusters(setup_test_data):
    """Test retrieving trending clusters."""
    await setup_test_data

    repo = ClusterRepository()
    trending = await repo.get_trending_clusters(limit=5)

    assert len(trending) <= 5
    if len(trending) > 0:
        assert all(hasattr(c, 'cluster_id') for c in trending)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cluster_metadata_consistency(setup_test_data):
    """Test that cluster metadata is consistent with article assignments."""
    data = await setup_test_data
    cluster_id = data["cluster_id"]

    repo = ClusterRepository()

    # Get metadata
    cluster = await repo.get_cluster_metadata(cluster_id)
    assert cluster is not None

    # Get articles in cluster
    articles, _ = await repo.get_articles_in_cluster(cluster_id, limit=1000)

    # Verify article count matches
    assert len(articles) == cluster.article_count

    # Verify all articles have positive confidence scores
    assert all(a.confidence_score > 0 for a in articles)
    assert all(a.confidence_score <= 1 for a in articles)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_handle_nonexistent_cluster():
    """Test handling of nonexistent cluster."""
    repo = ClusterRepository()

    # Test getting nonexistent cluster metadata
    cluster = await repo.get_cluster_metadata("nonexistent-cluster-xyz")
    assert cluster is None

    # Test getting articles in nonexistent cluster
    articles, _ = await repo.get_articles_in_cluster("nonexistent-cluster-xyz", limit=10)
    assert len(articles) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_handle_large_cluster(setup_test_data):
    """Test handling of cluster with 100+ articles."""
    data = await setup_test_data

    # Create a larger cluster for testing
    import time
    test_id = str(int(time.time() * 1000))
    large_cluster_id = f"large-cluster-{test_id}"

    # Create 100 articles
    article_ids = [f"large-article-{test_id}-{i}" for i in range(100)]

    articles_to_save = []
    for i, article_id in enumerate(article_ids):
        article = ArticleModel(
            article_id=article_id,
            title=f"Large Article {i}",
            slug=f"large-article-{i}",
            source_id="test-source",
            original_url=f"https://example.com/large-{i}",
            published_at=now_timestamp() - (i * 3600),
            view_count=100 + i,
            created_at=now_timestamp(),
            updated_at=now_timestamp(),
        )
        articles_to_save.append(article)

    # Save all articles
    for article in articles_to_save:
        await asyncio.to_thread(article.save)

    # Create cluster metadata
    large_cluster = ClusterMetadataModel(
        cluster_id=large_cluster_id,
        label="Large Test Cluster",
        description="Test cluster with 100+ articles",
        article_count=len(article_ids),
        size_category="LARGE",
        diversity_score=0.50,
        keywords=["large", "test", "100+", "articles", "benchmark"],
        centroid_embedding=[0.1] * 1536,
        top_articles=[],
        created_at=now_timestamp(),
        updated_at=now_timestamp(),
        ttl=now_timestamp() + (7 * 86400),
    )
    await asyncio.to_thread(large_cluster.save)

    # Create assignments
    for i, article_id in enumerate(article_ids):
        assignment = ArticleClusterModel(
            cluster_id=large_cluster_id,
            article_id=article_id,
            confidence_score=0.85,
            assigned_at=now_timestamp(),
            ttl=now_timestamp() + (7 * 86400),
        )
        await asyncio.to_thread(assignment.save)

    # Test fetching all articles
    repo = ClusterRepository()
    all_articles, _ = await repo.get_articles_in_cluster(
        large_cluster_id, limit=1000
    )

    assert len(all_articles) == 100

    # Cleanup
    try:
        await asyncio.to_thread(large_cluster.delete)
        for article_id in article_ids:
            for assignment in ArticleClusterModel.query(large_cluster_id):
                await asyncio.to_thread(assignment.delete)
            article = await asyncio.to_thread(ArticleModel.get, article_id)
            await asyncio.to_thread(article.delete)
    except Exception as e:
        print(f"Large cluster cleanup error: {e}")
