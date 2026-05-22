"""Integration tests for Qdrant vector database services."""

import pytest
import asyncio
from uuid import uuid4

from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService


class TestEmbeddingService:
    """Test embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test single embedding generation."""
        service = EmbeddingService()

        text = "Artificial Intelligence is transforming technology industries"
        embedding = await service.generate_embedding(text)

        assert embedding is not None
        assert len(embedding) == 1536
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.asyncio
    async def test_prepare_text_for_embedding(self):
        """Test text preparation for embedding."""
        service = EmbeddingService()

        title = "AI Revolution"
        summary = "The latest in artificial intelligence"
        content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50

        prepared = service.prepare_text_for_embedding(title, summary, content)

        assert title in prepared
        assert summary in prepared
        assert len(prepared) > len(title)

    @pytest.mark.asyncio
    async def test_empty_text_embedding(self):
        """Test embedding with empty text."""
        service = EmbeddingService()

        embedding = await service.generate_embedding("")

        assert embedding is not None
        assert len(embedding) == 1536


class TestQdrantService:
    """Test Qdrant vector database operations."""

    @pytest.fixture
    async def qdrant_service(self):
        """Create Qdrant service instance and clean collection before each test."""
        service = QdrantService()

        # Clear collection before each test to avoid cross-test pollution
        if service.client:
            try:
                service.client.delete_collection(service.collection_name)
                service._ensure_collection_exists()
            except Exception:
                pass

        yield service

    @pytest.mark.asyncio
    async def test_qdrant_initialization(self, qdrant_service):
        """Test Qdrant client initialization."""
        assert qdrant_service.client is not None
        assert qdrant_service.embedding_dim == 1536

    @pytest.mark.asyncio
    async def test_index_article(self, qdrant_service):
        """Test article indexing."""
        article_id = str(uuid4())

        success = await qdrant_service.index_article(
            article_id=article_id,
            title="Test Article: AI Innovations",
            summary="An overview of recent AI breakthroughs",
            content="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            category="Technology",
            author="Test Author",
            published_at=1234567890,
            view_count=100,
            source_id="test.com",
        )

        assert success is True

        # Verify article exists
        exists = await qdrant_service.article_exists(article_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_update_article(self, qdrant_service):
        """Test article update."""
        article_id = str(uuid4())

        # Index article
        await qdrant_service.index_article(
            article_id=article_id,
            title="Original Title",
            summary="Original summary",
            content="Original content",
            category="Tech",
        )

        # Update article
        success = await qdrant_service.update_article(
            article_id=article_id,
            title="Updated Title",
            summary="Updated summary",
            content="Updated content",
            category="News",
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_delete_article(self, qdrant_service):
        """Test article deletion."""
        article_id = str(uuid4())

        # Index article
        await qdrant_service.index_article(
            article_id=article_id,
            title="Test Article",
            summary="Test summary",
            category="Tech",
        )

        # Delete article
        success = await qdrant_service.delete_article(article_id)
        assert success is True

        # Verify article is deleted
        exists = await qdrant_service.article_exists(article_id)
        assert exists is False

    @pytest.mark.asyncio
    async def test_dense_search(self, qdrant_service):
        """Test semantic dense search."""
        # Index test articles
        articles = [
            {
                "id": str(uuid4()),
                "title": "Machine Learning Fundamentals",
                "summary": "Introduction to ML concepts",
            },
            {
                "id": str(uuid4()),
                "title": "Python Programming Guide",
                "summary": "Learn Python from basics to advanced",
            },
        ]

        for article in articles:
            await qdrant_service.index_article(
                article_id=article["id"],
                title=article["title"],
                summary=article["summary"],
                category="Education",
            )

        # Search for machine learning content
        results = await qdrant_service.dense_search(
            query="machine learning and artificial intelligence",
            limit=5,
        )

        assert len(results) > 0
        assert results[0]["title"] == "Machine Learning Fundamentals"

    @pytest.mark.asyncio
    async def test_bm25_search(self, qdrant_service):
        """Test keyword BM25 search."""
        # Index test articles
        articles = [
            {
                "id": str(uuid4()),
                "title": "Python Deep Learning",
                "summary": "Advanced deep learning with Python",
            },
            {
                "id": str(uuid4()),
                "title": "JavaScript Frameworks",
                "summary": "Popular JS frameworks for web development",
            },
        ]

        for article in articles:
            await qdrant_service.index_article(
                article_id=article["id"],
                title=article["title"],
                summary=article["summary"],
                category="Tech",
            )

        # BM25 search for Python
        results = await qdrant_service.bm25_search(
            query="Python",
            limit=5,
        )

        assert len(results) > 0
        assert "Python" in results[0]["title"]

    @pytest.mark.asyncio
    async def test_hybrid_search(self, qdrant_service):
        """Test hybrid search combining dense and BM25."""
        # Index test articles
        articles = [
            {
                "id": str(uuid4()),
                "title": "Neural Networks and Deep Learning",
                "summary": "Comprehensive guide to neural networks",
            },
            {
                "id": str(uuid4()),
                "title": "Quantum Computing Revolution",
                "summary": "The future of quantum computing",
            },
        ]

        for article in articles:
            await qdrant_service.index_article(
                article_id=article["id"],
                title=article["title"],
                summary=article["summary"],
                category="AI",
            )

        # Hybrid search
        results = await qdrant_service.hybrid_search(
            query="deep learning neural networks",
            limit=5,
            dense_weight=0.6,
            bm25_weight=0.4,
        )

        assert len(results) > 0
        # First result should be about neural networks
        assert "Neural Networks" in results[0]["title"]

    @pytest.mark.asyncio
    async def test_collection_stats(self, qdrant_service):
        """Test collection statistics retrieval."""
        stats = await qdrant_service.get_collection_stats()

        assert "collection_name" in stats
        assert "points_count" in stats
        assert stats["points_count"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
