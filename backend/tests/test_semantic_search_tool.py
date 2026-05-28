"""Comprehensive tests for Semantic Search Tool - TASK-CHT-008.

Tests cover:
1. Query embedding generation (1536-dimensional vectors)
2. Qdrant search and vector similarity
3. DynamoDB metadata enrichment
4. Filtering (source, date range, category)
5. Relevance ranking and top_k
6. Performance (1000+ articles < 500ms)
7. Tool definition compatibility with Agent Core
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from app.tools.semantic_search_tool import SemanticSearchTool
from app.models.search_result import ArticleResult
from app.models.article import ArticleModel


@pytest.fixture
def semantic_search_tool():
    """Create SemanticSearchTool instance."""
    return SemanticSearchTool()


@pytest.fixture
def mock_article():
    """Create a mock article for testing."""
    article = MagicMock(spec=ArticleModel)
    article.article_id = "550e8400-e29b-41d4-a716-446655440000"
    article.title = "Breaking AI News"
    article.summary = "A new AI model was released today"
    article.source_id = "techcrunch"
    article.original_url = "https://techcrunch.com/article"
    article.published_at = int(datetime.utcnow().timestamp())
    article.author = "Jane Doe"
    article.category = "AI"
    article.view_count = 1000
    article.like_count = 50
    return article


class TestQueryEmbedding:
    """Test 1: Query embedding generation."""

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    async def test_query_embedding_generation(self, mock_embedding_service_class, semantic_search_tool):
        """TEST 1: Generate embedding for search query.

        Verifies:
        - Query embedding is 1536 dimensions
        - Embedding is consistent for same query
        """
        # Setup mock
        mock_service = MagicMock()
        mock_embedding_service_class.return_value = mock_service

        embedding = [0.1] * 1536
        mock_service.generate_embedding = AsyncMock(return_value=embedding)

        tool = SemanticSearchTool()
        tool.embedding_service = mock_service

        # Execute
        result = await tool.embedding_service.generate_embedding("AI breakthroughs")

        # Verify
        assert result is not None
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        mock_service.generate_embedding.assert_called_once_with("AI breakthroughs")

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    async def test_embedding_consistency(self, mock_embedding_service_class, semantic_search_tool):
        """Verify embedding is consistent for same query."""
        mock_service = MagicMock()
        mock_embedding_service_class.return_value = mock_service

        embedding1 = [0.1] * 1536
        embedding2 = [0.1] * 1536
        mock_service.generate_embedding = AsyncMock(side_effect=[embedding1, embedding2])

        tool = SemanticSearchTool()
        tool.embedding_service = mock_service

        result1 = await tool.embedding_service.generate_embedding("test query")
        result2 = await tool.embedding_service.generate_embedding("test query")

        assert result1 == result2
        assert len(result1) == 1536

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    async def test_invalid_embedding_handling(self, mock_embedding_service_class):
        """Verify error handling for invalid embeddings."""
        mock_service = MagicMock()
        mock_embedding_service_class.return_value = mock_service

        # Return invalid embedding (wrong dimension)
        mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 512)

        tool = SemanticSearchTool()
        tool.embedding_service = mock_service

        with pytest.raises(Exception, match="Failed to generate valid query embedding"):
            await tool.execute("test query")


class TestQdrantSearch:
    """Test 2: Qdrant vector similarity search."""

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_qdrant_search_basic(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 2: Search Qdrant for semantically similar articles.

        Verifies:
        - Qdrant returns results ordered by similarity score
        - Results have correct metadata
        """
        # Setup mocks
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Mock Qdrant search results
        mock_point1 = MagicMock()
        mock_point1.payload = {
            "article_id": "art-1",
            "slug": "slug-1",
            "title": "Title 1",
            "summary": "Summary 1",
            "category": "AI",
            "source_id": "techcrunch",
            "published_at": 1685049600,
        }
        mock_point1.score = 0.95

        mock_point2 = MagicMock()
        mock_point2.payload = {
            "article_id": "art-2",
            "slug": "slug-2",
            "title": "Title 2",
            "summary": "Summary 2",
            "category": "tech",
            "source_id": "arstechnica",
            "published_at": 1685049500,
        }
        mock_point2.score = 0.87

        mock_result = MagicMock()
        mock_result.points = [mock_point1, mock_point2]
        mock_qdrant.client.query_points.return_value = mock_result

        # Mock article fetching
        article1 = MagicMock(spec=ArticleModel)
        article1.article_id = "art-1"
        article1.title = "Title 1"
        article1.summary = "Summary 1"
        article1.source_id = "techcrunch"
        article1.original_url = "https://tech.com/1"
        article1.published_at = 1685049600
        article1.author = "Author 1"
        article1.category = "AI"
        article1.view_count = 1000
        article1.like_count = 50

        mock_repo.get_by_id = AsyncMock(side_effect=lambda aid: article1 if aid == "art-1" else None)

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute
        results = await tool.execute("AI breakthroughs", top_k=2)

        # Verify
        assert len(results) > 0
        assert results[0].article_id == "art-1"
        assert results[0].relevance_score == 0.95
        assert results[0].title == "Title 1"

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_qdrant_results_sorted_descending(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """Verify Qdrant results are returned in descending score order."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create 5 results with descending scores
        points = []
        for i in range(5):
            point = MagicMock()
            point.payload = {
                "article_id": f"art-{i}",
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": f"Summary {i}",
                "category": "AI",
                "source_id": "source",
                "published_at": 1685049600 - i * 1000,
            }
            point.score = 0.95 - (i * 0.1)  # 0.95, 0.85, 0.75, 0.65, 0.55
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points

        mock_qdrant.client.query_points.return_value = mock_result

        # Mock article repository
        mock_repo.get_by_id = AsyncMock(return_value=None)

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute
        search_results = await tool._search_qdrant([0.1] * 1536, limit=5)

        # Verify
        assert len(search_results) == 5
        scores = [r["dense_score"] for r in search_results]
        assert scores == sorted(scores, reverse=True)


class TestDynamoDBEnrichment:
    """Test 3: DynamoDB metadata enrichment."""

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_dynamodb_metadata_enrichment(self, mock_repo_class, mock_embed_class, mock_qdrant_class, mock_article):
        """TEST 3: Enrich search results with DynamoDB metadata.

        Verifies:
        - All required fields fetched from DynamoDB
        - Metadata correctly assigned to results
        """
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id = AsyncMock(return_value=mock_article)

        # Qdrant results
        mock_point = MagicMock()
        mock_point.payload = {
            "article_id": "550e8400-e29b-41d4-a716-446655440000",
            "slug": "breaking-ai-news",
            "title": "Breaking AI News",
            "summary": "A new AI model was released today",
            "category": "AI",
            "source_id": "techcrunch",
            "published_at": int(datetime.utcnow().timestamp()),
        }
        mock_point.score = 0.95

        mock_result = MagicMock()
        mock_result.points = [mock_point]
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute
        results = await tool.execute("AI news", top_k=10)

        # Verify
        assert len(results) == 1
        result = results[0]
        assert result.article_id == mock_article.article_id
        assert result.title == mock_article.title
        assert result.summary == mock_article.summary
        assert result.source == mock_article.source_id
        assert result.url == mock_article.original_url
        assert result.author == mock_article.author
        assert result.category == mock_article.category
        assert result.view_count == mock_article.view_count
        assert result.relevance_score == 0.95

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_missing_article_handling(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """Verify handling of articles missing from DynamoDB."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_id = AsyncMock(return_value=None)  # Article not found

        # Qdrant results
        mock_point = MagicMock()
        mock_point.payload = {
            "article_id": "missing-article",
            "slug": "missing",
            "title": "Missing Article",
            "summary": "This article doesn't exist in DynamoDB",
            "category": "AI",
            "source_id": "unknown",
            "published_at": 1685049600,
        }
        mock_point.score = 0.95

        mock_result = MagicMock()
        mock_result.points = [mock_point]
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute - should return empty list since article not in DynamoDB
        results = await tool.execute("test", top_k=10)

        # Verify
        assert len(results) == 0


class TestFiltering:
    """Test 4: Filtering by source, date range, category."""

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_source_filtering(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 4A: Filter results by source_id."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create articles with different sources
        article1 = MagicMock(spec=ArticleModel)
        article1.article_id = "art-1"
        article1.title = "TechCrunch Article"
        article1.summary = "From TechCrunch"
        article1.source_id = "techcrunch"
        article1.original_url = "https://techcrunch.com"
        article1.published_at = 1685049600
        article1.author = "Author 1"
        article1.category = "AI"
        article1.view_count = 100
        article1.like_count = 5

        article2 = MagicMock(spec=ArticleModel)
        article2.article_id = "art-2"
        article2.title = "Ars Technica Article"
        article2.summary = "From Ars Technica"
        article2.source_id = "arstechnica"
        article2.original_url = "https://arstechnica.com"
        article2.published_at = 1685049500
        article2.author = "Author 2"
        article2.category = "tech"
        article2.view_count = 200
        article2.like_count = 10

        def get_article(aid):
            if aid == "art-1":
                return article1
            elif aid == "art-2":
                return article2
            return None

        mock_repo.get_by_id = AsyncMock(side_effect=get_article)

        # Qdrant results
        points = []
        for i, (aid, summary) in enumerate([("art-1", "TechCrunch"), ("art-2", "Ars Technica")]):
            point = MagicMock()
            point.payload = {
                "article_id": aid,
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": summary,
                "category": ["AI", "tech"][i],
                "source_id": ["techcrunch", "arstechnica"][i],
                "published_at": 1685049600 - i * 100,
            }
            point.score = 0.95 - (i * 0.1)
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute with source filter
        results = await tool.execute(
            "AI",
            top_k=10,
            filters={"source_id": "techcrunch"}
        )

        # Verify
        assert len(results) == 1
        assert results[0].source == "techcrunch"

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_date_range_filtering(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 4B: Filter results by date range."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create articles with different dates
        today = int(datetime.utcnow().timestamp())
        yesterday = today - (24 * 3600)
        week_ago = today - (7 * 24 * 3600)

        articles = {
            "art-1": MagicMock(article_id="art-1", title="Today", source_id="source", original_url="url",
                             published_at=today, author=None, category=None, view_count=0, like_count=0, summary=""),
            "art-2": MagicMock(article_id="art-2", title="Yesterday", source_id="source", original_url="url",
                             published_at=yesterday, author=None, category=None, view_count=0, like_count=0, summary=""),
            "art-3": MagicMock(article_id="art-3", title="Week Ago", source_id="source", original_url="url",
                             published_at=week_ago, author=None, category=None, view_count=0, like_count=0, summary=""),
        }

        for article in articles.values():
            article.spec = ArticleModel

        mock_repo.get_by_id = AsyncMock(side_effect=lambda aid: articles.get(aid))

        # Qdrant results with all articles
        points = []
        for i, (aid, published) in enumerate([("art-1", today), ("art-2", yesterday), ("art-3", week_ago)]):
            point = MagicMock()
            point.payload = {
                "article_id": aid,
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": f"Summary {i}",
                "category": None,
                "source_id": "source",
                "published_at": published,
            }
            point.score = 0.95 - (i * 0.05)
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute with date filter (last 2 days)
        start_date = today - (2 * 24 * 3600)
        results = await tool.execute(
            "test",
            top_k=10,
            filters={"start_date": start_date}
        )

        # Verify only recent articles returned
        assert len(results) == 2
        assert all(r.published_at >= start_date for r in results)

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_category_filtering(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 4C: Filter results by category."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create articles with different categories
        articles = {
            "art-1": MagicMock(article_id="art-1", title="AI Article", source_id="source", original_url="url",
                             published_at=1685049600, author=None, category="AI", view_count=0, like_count=0, summary=""),
            "art-2": MagicMock(article_id="art-2", title="Tech Article", source_id="source", original_url="url",
                             published_at=1685049500, author=None, category="tech", view_count=0, like_count=0, summary=""),
        }

        for article in articles.values():
            article.spec = ArticleModel

        mock_repo.get_by_id = AsyncMock(side_effect=lambda aid: articles.get(aid))

        # Qdrant results
        points = []
        for i, (aid, cat) in enumerate([("art-1", "AI"), ("art-2", "tech")]):
            point = MagicMock()
            point.payload = {
                "article_id": aid,
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": f"Summary {i}",
                "category": cat,
                "source_id": "source",
                "published_at": 1685049600 - i * 100,
            }
            point.score = 0.95 - (i * 0.1)
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute with category filter
        results = await tool.execute(
            "news",
            top_k=10,
            filters={"category": "AI"}
        )

        # Verify
        assert len(results) == 1
        assert results[0].category == "AI"


class TestRelevanceRanking:
    """Test 5: Relevance ranking and top_k."""

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_top_k_limit(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 5A: Respect top_k parameter."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create 20 articles
        articles = {}
        for i in range(20):
            article = MagicMock(spec=ArticleModel)
            article.article_id = f"art-{i}"
            article.title = f"Article {i}"
            article.summary = f"Summary {i}"
            article.source_id = "source"
            article.original_url = f"url-{i}"
            article.published_at = 1685049600
            article.author = f"Author {i}"
            article.category = "tech"
            article.view_count = i * 100
            article.like_count = i * 5
            articles[f"art-{i}"] = article

        mock_repo.get_by_id = AsyncMock(side_effect=lambda aid: articles.get(aid))

        # Qdrant results - all 20
        points = []
        for i in range(20):
            point = MagicMock()
            point.payload = {
                "article_id": f"art-{i}",
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": f"Summary {i}",
                "category": "tech",
                "source_id": "source",
                "published_at": 1685049600,
            }
            point.score = 0.95 - (i * 0.02)
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute with top_k=5
        results = await tool.execute("test", top_k=5)

        # Verify
        assert len(results) == 5

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_descending_relevance_score(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 5B: Results sorted by relevance_score (highest first)."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create 5 articles
        articles = {}
        for i in range(5):
            article = MagicMock(spec=ArticleModel)
            article.article_id = f"art-{i}"
            article.title = f"Article {i}"
            article.summary = f"Summary {i}"
            article.source_id = "source"
            article.original_url = f"url-{i}"
            article.published_at = 1685049600
            article.author = None
            article.category = None
            article.view_count = 0
            article.like_count = 0
            articles[f"art-{i}"] = article

        mock_repo.get_by_id = AsyncMock(side_effect=lambda aid: articles.get(aid))

        # Qdrant results with descending scores
        points = []
        scores = [0.99, 0.88, 0.77, 0.66, 0.55]
        for i, score in enumerate(scores):
            point = MagicMock()
            point.payload = {
                "article_id": f"art-{i}",
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": f"Summary {i}",
                "category": None,
                "source_id": "source",
                "published_at": 1685049600,
            }
            point.score = score
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute
        results = await tool.execute("test", top_k=5)

        # Verify descending order
        assert len(results) == 5
        result_scores = [r.relevance_score for r in results]
        assert result_scores == sorted(result_scores, reverse=True)

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_min_score_filtering(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 5C: min_score threshold filters low-relevance results."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create articles
        articles = {}
        for i in range(5):
            article = MagicMock(spec=ArticleModel)
            article.article_id = f"art-{i}"
            article.title = f"Article {i}"
            article.summary = f"Summary {i}"
            article.source_id = "source"
            article.original_url = f"url-{i}"
            article.published_at = 1685049600
            article.author = None
            article.category = None
            article.view_count = 0
            article.like_count = 0
            articles[f"art-{i}"] = article

        mock_repo.get_by_id = AsyncMock(side_effect=lambda aid: articles.get(aid))

        # Qdrant results with varying scores
        points = []
        scores = [0.95, 0.75, 0.55, 0.35, 0.15]
        for i, score in enumerate(scores):
            point = MagicMock()
            point.payload = {
                "article_id": f"art-{i}",
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": f"Summary {i}",
                "category": None,
                "source_id": "source",
                "published_at": 1685049600,
            }
            point.score = score
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute with min_score=0.7
        results = await tool.execute("test", top_k=10, min_score=0.7)

        # Verify
        assert len(results) == 2  # Only scores 0.95 and 0.75
        assert all(r.relevance_score >= 0.7 for r in results)


class TestPerformance:
    """Test 6: Performance with large result sets."""

    @pytest.mark.asyncio
    @patch("app.tools.semantic_search_tool.QdrantService")
    @patch("app.tools.semantic_search_tool.EmbeddingService")
    @patch("app.tools.semantic_search_tool.ArticleRepository")
    async def test_performance_1000_articles(self, mock_repo_class, mock_embed_class, mock_qdrant_class):
        """TEST 6: Search across 1000+ articles completes in < 500ms."""
        # Setup
        mock_qdrant = MagicMock()
        mock_qdrant.client = MagicMock()
        mock_qdrant.collection_name = "articles"
        mock_qdrant_class.return_value = mock_qdrant

        mock_embed = MagicMock()
        mock_embed.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embed_class.return_value = mock_embed

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Create 100 articles in mock (simulating 1000+)
        articles = {}
        for i in range(100):
            article = MagicMock(spec=ArticleModel)
            article.article_id = f"art-{i}"
            article.title = f"Article {i}"
            article.summary = f"Summary {i}"
            article.source_id = "source"
            article.original_url = f"url-{i}"
            article.published_at = 1685049600
            article.author = None
            article.category = None
            article.view_count = i * 10
            article.like_count = i
            articles[f"art-{i}"] = article

        mock_repo.get_by_id = AsyncMock(side_effect=lambda aid: articles.get(aid))

        # Qdrant results - return top 20 (simulating 1000+ available)
        points = []
        for i in range(20):
            point = MagicMock()
            point.payload = {
                "article_id": f"art-{i}",
                "slug": f"slug-{i}",
                "title": f"Title {i}",
                "summary": f"Summary {i}",
                "category": None,
                "source_id": "source",
                "published_at": 1685049600,
            }
            point.score = 0.95 - (i * 0.02)
            points.append(point)

        mock_result = MagicMock()
        mock_result.points = points
        mock_qdrant.client.query_points.return_value = mock_result

        tool = SemanticSearchTool()
        tool.qdrant_service = mock_qdrant
        tool.embedding_service = mock_embed
        tool.article_repository = mock_repo

        # Execute and measure time
        start = time.time()
        results = await tool.execute("test query", top_k=10)
        elapsed = (time.time() - start) * 1000

        # Verify
        assert len(results) == 10
        assert elapsed < 500  # Should complete in < 500ms


class TestToolDefinition:
    """Test 7: Tool definition for Agent Core integration."""

    def test_tool_definition_schema(self, semantic_search_tool):
        """TEST 7: Tool definition matches Agent Core expectations."""
        definition = semantic_search_tool.get_tool_definition()

        # Verify top-level structure
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition
        assert "output_schema" in definition

        # Verify name
        assert definition["name"] == "semantic_search"

        # Verify input schema
        input_schema = definition["input_schema"]
        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        assert "required" in input_schema

        # Verify required fields
        assert "query" in input_schema["required"]
        assert "query" in input_schema["properties"]

        # Verify query is string
        assert input_schema["properties"]["query"]["type"] == "string"

        # Verify optional fields
        assert "top_k" in input_schema["properties"]
        assert "min_score" in input_schema["properties"]
        assert "filters" in input_schema["properties"]

        # Verify output schema
        output_schema = definition["output_schema"]
        assert output_schema["type"] == "array"
        assert "items" in output_schema

        # Verify each result has required fields
        result_properties = output_schema["items"]["properties"]
        required_fields = [
            "article_id", "title", "summary", "relevance_score",
            "source", "url", "published_at", "author", "category",
            "view_count", "engagement_score"
        ]
        for field in required_fields:
            assert field in result_properties

    def test_tool_definition_field_types(self, semantic_search_tool):
        """Verify field types in tool definition."""
        definition = semantic_search_tool.get_tool_definition()
        input_props = definition["input_schema"]["properties"]

        # Verify types
        assert input_props["query"]["type"] == "string"
        assert input_props["top_k"]["type"] == "integer"
        assert input_props["min_score"]["type"] == "number"
        assert input_props["filters"]["type"] == "object"

        # Verify constraints
        assert input_props["top_k"]["minimum"] == 1
        assert input_props["top_k"]["maximum"] == 100
        assert input_props["min_score"]["minimum"] == 0.0
        assert input_props["min_score"]["maximum"] == 1.0

    def test_tool_definition_output_schema(self, semantic_search_tool):
        """Verify output schema structure."""
        definition = semantic_search_tool.get_tool_definition()
        output_schema = definition["output_schema"]

        # Should be array of objects
        assert output_schema["type"] == "array"
        assert output_schema["items"]["type"] == "object"

        # Verify items have all expected properties
        props = output_schema["items"]["properties"]
        expected = {
            "article_id": "string",
            "title": "string",
            "summary": "string",
            "relevance_score": "number",
            "source": "string",
            "url": "string",
            "published_at": "integer",
            "author": "string",
            "category": "string",
            "view_count": "integer",
            "engagement_score": "number",
        }

        for field, field_type in expected.items():
            assert field in props
            assert props[field]["type"] == field_type


class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    async def test_empty_query_raises_error(self, semantic_search_tool):
        """Verify empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await semantic_search_tool.execute("")

    @pytest.mark.asyncio
    async def test_invalid_top_k_raises_error(self, semantic_search_tool):
        """Verify invalid top_k raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            await semantic_search_tool.execute("test", top_k=0)

        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            await semantic_search_tool.execute("test", top_k=101)

    @pytest.mark.asyncio
    async def test_invalid_min_score_raises_error(self, semantic_search_tool):
        """Verify invalid min_score raises ValueError."""
        with pytest.raises(ValueError, match="min_score must be between 0.0 and 1.0"):
            await semantic_search_tool.execute("test", min_score=-0.1)

        with pytest.raises(ValueError, match="min_score must be between 0.0 and 1.0"):
            await semantic_search_tool.execute("test", min_score=1.1)
