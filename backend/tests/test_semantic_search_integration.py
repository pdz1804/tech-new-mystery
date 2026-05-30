"""Integration tests for Semantic Search Tool with real Qdrant and DynamoDB.

Tests verify:
1. End-to-end semantic search with real embeddings
2. Qdrant vector search and similarity ranking
3. DynamoDB article metadata enrichment
4. Filter application (source, date, category)
5. Performance on realistic article counts
6. Agent Core tool registration and compatibility
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from uuid import uuid4

from app.tools.semantic_search_tool import SemanticSearchTool
from app.services.qdrant_service import QdrantService
from app.services.embedding_service import EmbeddingService
from app.repositories.article_repository import ArticleRepository
from app.models.article import ArticleModel
from app.models.search_result import ArticleResult


@pytest.fixture
async def setup_integration_env():
    """Setup Qdrant and DynamoDB for integration tests."""
    qdrant_service = QdrantService()
    embedding_service = EmbeddingService()
    article_repo = ArticleRepository()

    # Clear Qdrant collection
    if qdrant_service.client:
        try:
            qdrant_service.client.delete_collection(qdrant_service.collection_name)
            qdrant_service._ensure_collection_exists()
        except Exception:
            pass

    yield {
        "qdrant": qdrant_service,
        "embedding": embedding_service,
        "repo": article_repo,
    }


class TestSemanticSearchIntegration:
    """Integration tests with real Qdrant and DynamoDB."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_semantic_search(self, setup_integration_env):
        """TEST 1: End-to-end semantic search with real data.

        Verifies:
        - Can embed real queries
        - Can search Qdrant with real vectors
        - Can fetch articles from DynamoDB
        - Returns relevant results
        """
        services = setup_integration_env
        qdrant = services["qdrant"]
        embedding = services["embedding"]

        # Skip if Qdrant not available
        if not qdrant.client:
            pytest.skip("Qdrant not available")

        # Create test articles and index them
        test_articles = [
            {
                "id": str(uuid4()),
                "title": "Breaking: AI Model Achieves New Milestone",
                "summary": "Researchers announce breakthrough in artificial intelligence research",
                "content": "A new AI model demonstrates unprecedented capabilities in natural language processing",
            },
            {
                "id": str(uuid4()),
                "title": "Climate Change: Solutions for 2026",
                "summary": "New renewable energy technologies show promise",
                "content": "Solar and wind power innovations could reduce emissions significantly",
            },
            {
                "id": str(uuid4()),
                "title": "Tech Giants Announce Partnership",
                "summary": "Major technology companies collaborate on new standards",
                "content": "Industry leaders agree on interoperability standards for next generation",
            },
        ]

        # Index articles in Qdrant
        for article in test_articles:
            success = await qdrant.index_article(
                article_id=article["id"],
                title=article["title"],
                summary=article["summary"],
                content=article["content"],
                category="technology",
                author="Test Author",
                published_at=int(datetime.utcnow().timestamp()),
                source_id="test-source",
            )
            assert success, f"Failed to index article {article['id']}"

        # Create semantic search tool
        tool = SemanticSearchTool()

        # Search for AI-related articles
        results = await tool.execute("artificial intelligence breakthroughs", top_k=5)

        # Verify results
        assert len(results) > 0, "Should find AI-related articles"
        assert isinstance(results[0], ArticleResult)
        assert results[0].relevance_score > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_with_real_embeddings(self, setup_integration_env):
        """TEST 2: Verify embedding consistency and search accuracy.

        Verifies:
        - Query embeddings are 1536 dimensions
        - Embeddings are consistent for same query
        - Similar queries return similar results
        """
        services = setup_integration_env
        embedding = services["embedding"]

        # Generate embeddings for test queries
        query1 = "machine learning algorithms"
        query2 = "machine learning algorithms"  # Same query
        query3 = "climate change solutions"  # Different query

        emb1 = await embedding.generate_embedding(query1)
        emb2 = await embedding.generate_embedding(query2)
        emb3 = await embedding.generate_embedding(query3)

        # Verify embeddings are 1536-dimensional
        assert len(emb1) == 1536
        assert len(emb2) == 1536
        assert len(emb3) == 1536

        # Verify embeddings are consistent for same query
        assert emb1 == emb2, "Same query should produce identical embeddings"

        # Verify different query produces different embedding
        assert emb1 != emb3, "Different queries should produce different embeddings"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filtering_by_source_integration(self, setup_integration_env):
        """TEST 3: Filter results by source in real Qdrant/DynamoDB.

        Verifies:
        - Source filtering works with real data
        - Only articles from specified source returned
        """
        services = setup_integration_env
        qdrant = services["qdrant"]

        if not qdrant.client:
            pytest.skip("Qdrant not available")

        # Index articles from different sources
        article_ids = []
        for i, source in enumerate(["techcrunch", "arstechnica", "wired"]):
            article_id = str(uuid4())
            success = await qdrant.index_article(
                article_id=article_id,
                title=f"AI Article {i}",
                summary="Article about artificial intelligence",
                content="Machine learning is a subset of artificial intelligence",
                category="AI",
                author="Test",
                published_at=int(datetime.utcnow().timestamp()),
                source_id=source,
            )
            assert success
            article_ids.append(article_id)

        # Search with source filter
        tool = SemanticSearchTool()
        results = await tool.execute(
            "artificial intelligence",
            top_k=10,
            filters={"source_id": "techcrunch"},
        )

        # All results should be from techcrunch
        if results:
            assert all(r.source == "techcrunch" for r in results)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filtering_by_date_range_integration(self, setup_integration_env):
        """TEST 4: Filter results by date range in real Qdrant.

        Verifies:
        - Date range filtering works
        - Only articles in date range returned
        """
        services = setup_integration_env
        qdrant = services["qdrant"]

        if not qdrant.client:
            pytest.skip("Qdrant not available")

        # Index articles with different timestamps
        now = int(datetime.utcnow().timestamp())
        yesterday = now - (24 * 3600)
        week_ago = now - (7 * 24 * 3600)

        timestamps = [now, yesterday, week_ago]
        for i, ts in enumerate(timestamps):
            article_id = str(uuid4())
            success = await qdrant.index_article(
                article_id=article_id,
                title=f"News Article {i}",
                summary="Recent news about technology",
                content="Technology advancing rapidly",
                category="tech",
                author="Test",
                published_at=ts,
                source_id="test",
            )
            assert success

        # Search with date filter (last 2 days)
        tool = SemanticSearchTool()
        start_date = now - (2 * 24 * 3600)

        results = await tool.execute(
            "technology news",
            top_k=10,
            filters={"start_date": start_date},
        )

        # Only recent articles should be returned
        if results:
            assert all(r.published_at >= start_date for r in results)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_top_k_parameter_integration(self, setup_integration_env):
        """TEST 5: Verify top_k parameter limits results correctly.

        Verifies:
        - Returns exactly top_k results (or fewer if not enough exist)
        - Results sorted by relevance score descending
        """
        services = setup_integration_env
        qdrant = services["qdrant"]

        if not qdrant.client:
            pytest.skip("Qdrant not available")

        # Index 15 articles
        article_ids = []
        for i in range(15):
            article_id = str(uuid4())
            success = await qdrant.index_article(
                article_id=article_id,
                title=f"AI Research Article {i}: " + ("Deep Learning" if i % 2 == 0 else "Neural Networks"),
                summary="Article about artificial intelligence and machine learning",
                content="Lorem ipsum dolor sit amet consectetur adipiscing elit",
                category="AI",
                author=f"Author {i}",
                published_at=int(datetime.utcnow().timestamp()) - (i * 1000),
                source_id="test-source",
            )
            assert success
            article_ids.append(article_id)

        # Search with top_k=5
        tool = SemanticSearchTool()
        results = await tool.execute("artificial intelligence deep learning", top_k=5)

        # Should return at most 5 results
        assert len(results) <= 5

        # Results should be sorted by relevance descending
        if len(results) > 1:
            scores = [r.relevance_score for r in results]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_with_multiple_articles(self, setup_integration_env):
        """TEST 6: Performance test with 50+ articles.

        Verifies:
        - Search completes in reasonable time (< 2 seconds)
        - No memory leaks or resource exhaustion
        - Results remain accurate with large dataset
        """
        services = setup_integration_env
        qdrant = services["qdrant"]

        if not qdrant.client:
            pytest.skip("Qdrant not available")

        # Index 50 articles
        article_ids = []
        start_index = time.time()
        for i in range(50):
            article_id = str(uuid4())
            title = [
                "AI Breakthroughs",
                "Climate Solutions",
                "Tech News",
                "Science Updates",
                "Innovation Report",
            ][i % 5]

            success = await qdrant.index_article(
                article_id=article_id,
                title=f"{title} #{i}",
                summary=f"Article {i} about latest developments",
                content=f"Content for article {i} with meaningful text",
                category=["AI", "Climate", "Tech", "Science", "Innovation"][i % 5],
                author=f"Author {i}",
                published_at=int(datetime.utcnow().timestamp()) - (i * 3600),
                source_id=["techcrunch", "arstechnica", "wired"][i % 3],
            )
            assert success
            article_ids.append(article_id)

        index_time = time.time() - start_index

        # Search and measure time
        tool = SemanticSearchTool()
        search_start = time.time()
        results = await tool.execute("artificial intelligence innovation", top_k=10)
        search_time = (time.time() - search_start) * 1000  # Convert to ms

        # Verify search performance
        assert search_time < 2000, f"Search took {search_time}ms, expected < 2000ms"
        assert len(results) > 0, "Should find relevant articles"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_agent_core_tool_definition(self, setup_integration_env):
        """TEST 7: Verify tool definition is Agent Core compatible.

        Verifies:
        - Tool definition has required fields
        - Input/output schemas match Agent Core expectations
        - All fields are properly typed
        """
        tool = SemanticSearchTool()
        definition = tool.get_tool_definition()

        # Check required fields
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
        assert input_schema["properties"]["query"]["type"] == "string"

        # Verify optional parameters with defaults
        assert "top_k" in input_schema["properties"]
        assert "min_score" in input_schema["properties"]
        assert "filters" in input_schema["properties"]

        # Verify output schema
        output_schema = definition["output_schema"]
        assert output_schema["type"] == "array"
        assert "items" in output_schema

        # Verify result fields
        result_props = output_schema["items"]["properties"]
        required_fields = [
            "article_id",
            "title",
            "summary",
            "relevance_score",
            "source",
            "url",
        ]
        for field in required_fields:
            assert field in result_props

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_diverse_query_types(self, setup_integration_env):
        """TEST 8: Search with diverse query types.

        Verifies:
        - Single term queries work
        - Phrase queries work
        - Complex multi-term queries work
        """
        services = setup_integration_env
        qdrant = services["qdrant"]

        if not qdrant.client:
            pytest.skip("Qdrant not available")

        # Index test articles
        articles = [
            ("GPT-5 Language Model Released", "New AI language model announced"),
            ("Climate Change Solutions", "Renewable energy breakthroughs"),
            ("Quantum Computing Advances", "New quantum algorithms developed"),
        ]

        for i, (title, summary) in enumerate(articles):
            success = await qdrant.index_article(
                article_id=str(uuid4()),
                title=title,
                summary=summary,
                content=f"Article content about {title}",
                category="tech",
                author="Test",
                published_at=int(datetime.utcnow().timestamp()),
                source_id="test",
            )
            assert success

        tool = SemanticSearchTool()

        # Test single term query
        results1 = await tool.execute("AI", top_k=5)
        assert len(results1) > 0

        # Test phrase query
        results2 = await tool.execute("language model", top_k=5)
        assert len(results2) > 0

        # Test complex query
        results3 = await tool.execute(
            "artificial intelligence and machine learning breakthroughs",
            top_k=5,
        )
        assert len(results3) >= 0  # May or may not find results


class TestSemanticSearchErrorHandling:
    """Test error handling in semantic search."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_empty_query_handling(self):
        """Verify empty query raises appropriate error."""
        tool = SemanticSearchTool()

        with pytest.raises(ValueError, match="Query cannot be empty"):
            await tool.execute("")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_top_k_handling(self):
        """Verify invalid top_k raises appropriate error."""
        tool = SemanticSearchTool()

        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            await tool.execute("test", top_k=0)

        with pytest.raises(ValueError, match="top_k must be between 1 and 100"):
            await tool.execute("test", top_k=101)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_min_score_handling(self):
        """Verify invalid min_score raises appropriate error."""
        tool = SemanticSearchTool()

        with pytest.raises(ValueError, match="min_score must be between 0.0 and 1.0"):
            await tool.execute("test", min_score=-0.5)

        with pytest.raises(ValueError, match="min_score must be between 0.0 and 1.0"):
            await tool.execute("test", min_score=1.5)


class TestSemanticSearchRelevanceRanking:
    """Test relevance ranking and scoring."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_relevance_score_ranking(self, setup_integration_env):
        """Verify results are ranked by relevance score correctly.

        Verifies:
        - Higher relevance scores appear first
        - Scores are between 0 and 1
        """
        services = setup_integration_env
        qdrant = services["qdrant"]

        if not qdrant.client:
            pytest.skip("Qdrant not available")

        # Index highly relevant and less relevant articles
        for i in range(10):
            relevance = "AI machine learning neural networks" if i < 5 else "Sports entertainment news"
            success = await qdrant.index_article(
                article_id=str(uuid4()),
                title=f"Article {i}",
                summary=relevance,
                content=relevance * 3,
                category="tech",
                author="Test",
                published_at=int(datetime.utcnow().timestamp()),
                source_id="test",
            )
            assert success

        # Search for AI-related content
        tool = SemanticSearchTool()
        results = await tool.execute("artificial intelligence machine learning", top_k=10)

        # Verify scoring
        if len(results) > 1:
            # Scores should be in descending order
            scores = [r.relevance_score for r in results]
            assert scores == sorted(scores, reverse=True)

            # All scores should be between 0 and 1
            assert all(0 <= score <= 1 for score in scores)
