"""Tests for cluster API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.api.v1.clusters.schemas import (
    ClusterSummary,
    ClusterDetail,
    ClusterArticlesResponse,
    TrendingClustersResponse,
    PaginationInfo,
    TopArticleItem,
)
from app.models.clustering import ArticleClusterModel, ClusterMetadataModel, TopArticleItem as TopArticleItemModel
from app.models.article import ArticleModel


@pytest.fixture
def mock_cluster_metadata():
    """Create mock cluster metadata."""
    cluster = MagicMock(spec=ClusterMetadataModel)
    cluster.cluster_id = "cluster-001"
    cluster.label = "AI Breakthroughs & LLM Development"
    cluster.description = "Recent advances in large language models"
    cluster.article_count = 23
    cluster.size_category = "MEDIUM"
    cluster.diversity_score = 0.42
    cluster.keywords = ["AI", "LLM", "GPT-5", "transformer", "training"]
    cluster.created_at = 1717008000
    cluster.updated_at = 1717008000

    # Mock top articles
    top_article = MagicMock(spec=TopArticleItemModel)
    top_article.article_id = "article-xyz"
    top_article.title = "GPT-5 Training Complete..."
    top_article.engagement_score = 4.2
    cluster.top_articles = [top_article]

    return cluster


@pytest.fixture
def mock_article_assignment():
    """Create mock article cluster assignment."""
    assignment = MagicMock(spec=ArticleClusterModel)
    assignment.cluster_id = "cluster-001"
    assignment.article_id = "article-xyz"
    assignment.confidence_score = 0.89
    assignment.assigned_at = 1717008000

    return assignment


@pytest.fixture
def mock_article():
    """Create mock article."""
    article = MagicMock(spec=ArticleModel)
    article.article_id = "article-xyz"
    article.title = "GPT-5 Training Complete..."
    article.summary = "Leading AI lab announces completion..."
    article.source_id = "techcrunch"
    article.published_at = 1717005600
    article.view_count = 1500
    article.preview_image = "https://example.com/image.jpg"
    article.original_url = "https://techcrunch.com/..."

    return article


@pytest.mark.asyncio
async def test_list_clusters_success(mock_cluster_metadata, client):
    """Test successful list clusters request."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # Mock repository methods
        mock_repo.count_clusters.return_value = 45
        mock_repo.list_cluster_metadata.return_value = (
            [mock_cluster_metadata] * 20,
            None,
        )

        response = client.get("/v1/clusters?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()

        assert "clusters" in data
        assert "pagination" in data
        assert len(data["clusters"]) == 20
        assert data["pagination"]["total_count"] == 45
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20


@pytest.mark.asyncio
async def test_list_clusters_pagination():
    """Test pagination parameters validation."""
    response = client.get("/v1/clusters?page=0&page_size=20")
    assert response.status_code == 422  # Validation error

    response = client.get("/v1/clusters?page=1&page_size=101")
    assert response.status_code == 422  # Validation error (max 100)


@pytest.mark.asyncio
async def test_list_clusters_sorting():
    """Test different sort options."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        mock_repo.count_clusters.return_value = 10
        mock_repo.list_cluster_metadata.return_value = ([], None)

        # Test sort_by parameter
        for sort in ["size", "recency", "diversity"]:
            response = client.get(f"/v1/clusters?sort_by={sort}")
            assert response.status_code == 200

        # Test invalid sort
        response = client.get("/v1/clusters?sort_by=invalid")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_cluster_detail_success(mock_cluster_metadata, mock_article_assignment, mock_article):
    """Test successful get cluster detail request."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_cluster_repo_class, \
         patch("app.api.v1.clusters.router.ArticleRepository") as mock_article_repo_class:

        mock_cluster_repo = AsyncMock()
        mock_article_repo = AsyncMock()
        mock_cluster_repo_class.return_value = mock_cluster_repo
        mock_article_repo_class.return_value = mock_article_repo

        # Setup mocks
        mock_cluster_repo.get_cluster_metadata.return_value = mock_cluster_metadata
        mock_cluster_repo.get_articles_in_cluster.return_value = (
            [mock_article_assignment] * 23,
            None,
        )
        mock_article_repo.get_articles_by_ids.return_value = [mock_article]

        response = client.get("/v1/clusters/cluster-001")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "cluster-001"
        assert data["label"] == "AI Breakthroughs & LLM Development"
        assert data["article_count"] == 23


@pytest.mark.asyncio
async def test_get_cluster_detail_not_found():
    """Test get cluster detail with non-existent cluster."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_cluster_metadata.return_value = None

        response = client.get("/v1/clusters/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_cluster_articles_success(mock_cluster_metadata, mock_article_assignment, mock_article):
    """Test successful get cluster articles request."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_cluster_repo_class, \
         patch("app.api.v1.clusters.router.ArticleRepository") as mock_article_repo_class:

        mock_cluster_repo = AsyncMock()
        mock_article_repo = AsyncMock()
        mock_cluster_repo_class.return_value = mock_cluster_repo
        mock_article_repo_class.return_value = mock_article_repo

        mock_cluster_repo.get_cluster_metadata.return_value = mock_cluster_metadata
        mock_cluster_repo.get_articles_in_cluster.return_value = (
            [mock_article_assignment] * 23,
            None,
        )
        mock_article_repo.get_articles_by_ids.return_value = [mock_article]

        response = client.get("/v1/clusters/cluster-001/articles?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()

        assert "articles" in data
        assert "pagination" in data


@pytest.mark.asyncio
async def test_get_cluster_articles_sorting():
    """Test different sort options for articles."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_cluster_repo_class, \
         patch("app.api.v1.clusters.router.ArticleRepository") as mock_article_repo_class:

        mock_cluster_repo = AsyncMock()
        mock_article_repo = AsyncMock()
        mock_cluster_repo_class.return_value = mock_cluster_repo
        mock_article_repo_class.return_value = mock_article_repo

        # Create a mock cluster
        cluster = MagicMock(spec=ClusterMetadataModel)
        cluster.cluster_id = "cluster-001"
        cluster.article_count = 10
        cluster.created_at = 1717008000
        cluster.updated_at = 1717008000

        mock_cluster_repo.get_cluster_metadata.return_value = cluster
        mock_cluster_repo.get_articles_in_cluster.return_value = ([], None)
        mock_article_repo.get_articles_by_ids.return_value = []

        # Test sort parameters
        for sort in ["date", "engagement", "title"]:
            response = client.get(f"/v1/clusters/cluster-001/articles?sort={sort}")
            assert response.status_code == 200

        # Test invalid sort
        response = client.get("/v1/clusters/cluster-001/articles?sort=invalid")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_trending_clusters_success(mock_cluster_metadata):
    """Test successful get trending clusters request."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        mock_repo.get_trending_clusters.return_value = [mock_cluster_metadata] * 5

        response = client.get("/v1/clusters/trending")

        assert response.status_code == 200
        data = response.json()

        assert "trending_clusters" in data
        assert len(data["trending_clusters"]) <= 5


@pytest.mark.asyncio
async def test_get_trending_clusters_limit():
    """Test trending clusters limit parameter."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        mock_repo.get_trending_clusters.return_value = []

        # Test limit parameter
        response = client.get("/v1/clusters/trending?limit=3")
        assert response.status_code == 200

        # Verify limit is capped at 5
        response = client.get("/v1/clusters/trending?limit=20")
        assert response.status_code == 200

        # Test invalid limit
        response = client.get("/v1/clusters/trending?limit=0")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_cluster_detail_pagination(mock_cluster_metadata, mock_article_assignment, mock_article):
    """Test pagination in cluster detail."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_cluster_repo_class, \
         patch("app.api.v1.clusters.router.ArticleRepository") as mock_article_repo_class:

        mock_cluster_repo = AsyncMock()
        mock_article_repo = AsyncMock()
        mock_cluster_repo_class.return_value = mock_cluster_repo
        mock_article_repo_class.return_value = mock_article_repo

        # Create 100 mock assignments
        assignments = [MagicMock(spec=ArticleClusterModel) for _ in range(100)]
        for i, a in enumerate(assignments):
            a.article_id = f"article-{i}"
            a.confidence_score = 0.8

        mock_cluster_metadata.article_count = 100

        mock_cluster_repo.get_cluster_metadata.return_value = mock_cluster_metadata
        mock_cluster_repo.get_articles_in_cluster.return_value = (assignments, None)

        # Create mock articles
        mock_articles = [MagicMock(spec=ArticleModel) for _ in range(100)]
        for i, a in enumerate(mock_articles):
            a.article_id = f"article-{i}"
            a.title = f"Article {i}"
            a.summary = f"Summary {i}"
            a.source_id = "source"
            a.published_at = 1717005600
            a.view_count = 100
            a.preview_image = None
            a.original_url = "https://example.com"

        mock_article_repo.get_articles_by_ids.return_value = mock_articles

        # Test pagination
        response = client.get("/v1/clusters/cluster-001?page=2&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 20
        assert data["pagination"]["total_count"] == 100


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling for API failures."""
    with patch("app.api.v1.clusters.router.ClusterRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # Test repository exception
        mock_repo.count_clusters.side_effect = Exception("Database error")

        response = client.get("/v1/clusters")

        assert response.status_code == 500
        assert "Failed to list clusters" in response.json()["detail"]
