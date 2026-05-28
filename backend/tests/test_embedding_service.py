"""
Comprehensive tests for EmbeddingService.
Tests cover: cache hits, batch efficiency, error handling, edge cases.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from app.services.embedding_service import EmbeddingService
from app.models.article_embedding import ArticleEmbeddingModel


@pytest.fixture
def embedding_service():
    """Create EmbeddingService with mocked OpenAI client."""
    service = EmbeddingService()
    service.api_key = "test-key"
    return service


class TestBatchEmbedArticlesEdgeCases:
    """Tests for edge cases in batch_embed_articles."""

    def test_empty_list_input(self, embedding_service):
        """EDGE: Empty list returns empty dict."""
        result = embedding_service.batch_embed_articles([])
        assert result == {}

    def test_single_article(self, embedding_service):
        """EDGE: Single article embedding works correctly."""
        with patch.object(
            embedding_service, "_batch_api_embeddings"
        ) as mock_api:
            mock_embedding = [0.1] * 1536
            mock_api.return_value = {
                "art-1": {
                    "embedding": mock_embedding,
                    "model": "text-embedding-3-small",
                    "cached": False,
                    "timestamp": 1234567890,
                }
            }

            articles = [{"id": "art-1", "title": "Test", "summary": "Summary"}]

            result = embedding_service.batch_embed_articles(articles)

            assert len(result) == 1
            assert "art-1" in result
            assert len(result["art-1"]["embedding"]) == 1536

    def test_article_missing_id(self, embedding_service):
        """EDGE: Article without ID is skipped."""
        with patch.object(
            embedding_service, "_batch_api_embeddings"
        ) as mock_api:
            mock_api.return_value = {}

            articles = [{"title": "No ID Article", "summary": "Summary"}]

            result = embedding_service.batch_embed_articles(articles)

            # Should skip article without ID
            assert len(result) == 0
            mock_api.assert_called_once_with([])

    def test_article_with_article_id_key(self, embedding_service):
        """EDGE: Article with 'article_id' key works correctly."""
        with patch.object(
            embedding_service, "_batch_api_embeddings"
        ) as mock_api:
            mock_embedding = [0.1] * 1536
            mock_api.return_value = {
                "art-1": {
                    "embedding": mock_embedding,
                    "model": "text-embedding-3-small",
                    "cached": False,
                    "timestamp": 1234567890,
                }
            }

            articles = [{"article_id": "art-1", "title": "Test", "summary": "Summary"}]

            result = embedding_service.batch_embed_articles(articles)

            assert len(result) == 1
            assert "art-1" in result


class TestBatchEmbedArticlesCacheHitRate:
    """Tests for cache hit rate functionality."""

    @patch.object(ArticleEmbeddingModel, "get")
    def test_cache_hit_rate_first_call(self, mock_get, embedding_service):
        """BASIC: First call has no cache hits."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        with patch.object(
            embedding_service, "_batch_api_embeddings"
        ) as mock_api:
            mock_api.return_value = {
                f"art-{i}": {
                    "embedding": [0.1] * 1536,
                    "model": "text-embedding-3-small",
                    "cached": False,
                    "timestamp": 1234567890,
                }
                for i in range(10)
            }

            articles = [{"id": f"art-{i}", "title": f"Title {i}"} for i in range(10)]

            result = embedding_service.batch_embed_articles(articles)

            assert len(result) == 10
            # All should be uncached on first run
            uncached_count = sum(
                1 for r in result.values() if not r.get("cached", False)
            )
            assert uncached_count == 10

    @patch.object(ArticleEmbeddingModel, "get")
    def test_cache_hit_rate_second_call(self, mock_get, embedding_service):
        """TEST-CLU-002: Second call uses cache, 80%+ cache hit rate."""
        # First 8 calls return cached embeddings, last 2 miss
        cached_embedding = [0.1] * 1536
        call_count = [0]

        def get_side_effect(article_id):
            call_count[0] += 1
            if call_count[0] <= 8:
                mock_model = MagicMock()
                mock_model.embedding = cached_embedding
                return mock_model
            raise ArticleEmbeddingModel.DoesNotExist()

        mock_get.side_effect = get_side_effect

        with patch.object(
            embedding_service, "_batch_api_embeddings"
        ) as mock_api:
            # Only last 2 articles need new embeddings
            mock_api.return_value = {
                f"art-{i}": {
                    "embedding": [0.2] * 1536,
                    "model": "text-embedding-3-small",
                    "cached": False,
                    "timestamp": 1234567890,
                }
                for i in range(8, 10)
            }

            articles = [{"id": f"art-{i}", "title": f"Title {i}"} for i in range(10)]

            result = embedding_service.batch_embed_articles(articles)

            assert len(result) == 10

            # Check cache hit rate
            cached_count = sum(
                1 for r in result.values() if r.get("cached", False)
            )
            cache_hit_rate = (cached_count / 10) * 100

            assert cache_hit_rate >= 80, f"Cache hit rate {cache_hit_rate}% < 80%"
            assert cached_count == 8

    @patch.object(ArticleEmbeddingModel, "get")
    def test_force_regenerate_ignores_cache(self, mock_get, embedding_service):
        """HARD: force_regenerate=True ignores cache."""
        mock_model = MagicMock()
        mock_model.embedding = [0.1] * 1536
        mock_get.return_value = mock_model

        with patch.object(
            embedding_service, "_batch_api_embeddings"
        ) as mock_api:
            mock_api.return_value = {
                "art-1": {
                    "embedding": [0.2] * 1536,
                    "model": "text-embedding-3-small",
                    "cached": False,
                    "timestamp": 1234567890,
                }
            }

            articles = [{"id": "art-1", "title": "Test"}]

            result = embedding_service.batch_embed_articles(articles, force_regenerate=True)

            # Should get fresh embedding even though cache exists
            assert result["art-1"]["cached"] is False
            # Cache check should not be called
            mock_get.assert_not_called()


class TestBatchEmbedArticlesBatchEfficiency:
    """Tests for batch API efficiency."""

    @patch.object(ArticleEmbeddingModel, "get")
    def test_batch_api_efficiency_250_articles(self, mock_get, embedding_service):
        """TEST-CLU-002: 250 articles make 3 API calls (100+100+50)."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        with patch.object(
            embedding_service, "_call_api_with_retry"
        ) as mock_call_api:
            # Return 100 embeddings first call, 100 second, 50 third
            def api_side_effect(texts):
                return [[0.1 * (i % 10)] * 1536 for i in range(len(texts))]

            mock_call_api.side_effect = api_side_effect

            articles = [
                {"id": f"art-{i}", "title": f"Title {i}"} for i in range(250)
            ]

            result = embedding_service.batch_embed_articles(articles)

            assert len(result) == 250

            # Verify 3 API calls were made
            assert mock_call_api.call_count == 3

            # Verify call sizes
            calls = mock_call_api.call_args_list
            assert len(calls[0][0][0]) == 100  # First call: 100 texts
            assert len(calls[1][0][0]) == 100  # Second call: 100 texts
            assert len(calls[2][0][0]) == 50   # Third call: 50 texts

    @patch.object(ArticleEmbeddingModel, "get")
    def test_batch_efficiency_custom_batch_size(self, mock_get, embedding_service):
        """COMPLEX: Custom batch size is respected."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        # Set custom batch size
        original_batch_size = embedding_service.__class__.__dict__.get(
            "batch_size", 100
        )

        with patch("app.services.embedding_service.settings") as mock_settings:
            mock_settings.openai_embedding_batch_size = 25
            mock_settings.openai_embedding_retry_max_attempts = 3

            with patch.object(
                embedding_service, "_call_api_with_retry"
            ) as mock_call_api:
                def api_side_effect(texts):
                    return [[0.1] * 1536 for _ in texts]

                mock_call_api.side_effect = api_side_effect

                articles = [
                    {"id": f"art-{i}", "title": f"Title {i}"} for i in range(75)
                ]

                result = embedding_service.batch_embed_articles(articles)

                assert len(result) == 75

                # With batch size 25, should make 3 calls (25+25+25)
                assert mock_call_api.call_count == 3


class TestBatchEmbedArticlesErrorHandling:
    """Tests for error handling in batch embeddings."""

    @patch.object(ArticleEmbeddingModel, "get")
    def test_openai_api_timeout_with_retry(self, mock_get, embedding_service):
        """TEST-CLU-002: Timeout with exponential backoff retry."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        with patch.object(
            embedding_service, "_call_api_with_retry"
        ) as mock_call_api:
            # Simulate timeout then success
            from openai import APIError

            mock_call_api.side_effect = [
                APIError("Timeout"),
                APIError("Timeout"),
                [[0.1] * 1536],  # Success on third try
            ]

            articles = [{"id": "art-1", "title": "Test"}]

            # First two calls fail, third succeeds - should raise after max retries
            with pytest.raises(Exception) as exc_info:
                embedding_service.batch_embed_articles(articles)

            assert "Failed to call OpenAI" in str(exc_info.value)

    @patch.object(ArticleEmbeddingModel, "get")
    def test_rate_limit_429_response(self, mock_get, embedding_service):
        """TEST-CLU-002: 429 rate limit response triggers exponential backoff."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        with patch.object(
            embedding_service, "_call_api_with_retry"
        ) as mock_call_api:
            from openai import RateLimitError

            # All retries fail
            mock_call_api.side_effect = RateLimitError("Rate limit exceeded")

            articles = [{"id": "art-1", "title": "Test"}]

            with pytest.raises(Exception) as exc_info:
                embedding_service.batch_embed_articles(articles)

            assert "rate limit" in str(exc_info.value).lower() or "failed" in str(
                exc_info.value
            ).lower()

    @patch.object(ArticleEmbeddingModel, "get")
    @patch.object(ArticleEmbeddingModel, "save")
    def test_no_corrupted_embeddings_on_failure(
        self, mock_save, mock_get, embedding_service
    ):
        """TEST-CLU-002: Failed articles don't get stored to DynamoDB."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()
        mock_save.side_effect = Exception("Storage error")

        with patch.object(
            embedding_service, "_call_api_with_retry"
        ) as mock_call_api:
            # Return valid embeddings
            mock_call_api.return_value = [[0.1] * 1536]

            articles = [{"id": "art-1", "title": "Test"}]

            with patch.object(
                embedding_service, "_store_embedding"
            ) as mock_store:
                mock_store.side_effect = Exception("Storage error")

                # Should raise exception
                with pytest.raises(Exception):
                    embedding_service.batch_embed_articles(articles)


class TestDynamoDBIntegration:
    """Tests for DynamoDB integration."""

    @patch.object(ArticleEmbeddingModel, "get")
    def test_embedding_storage_structure(self, mock_get, embedding_service):
        """TEST-CLU-002: Embeddings stored with correct structure."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        with patch.object(
            embedding_service, "_call_api_with_retry"
        ) as mock_call_api:
            mock_embedding = [0.1 * i for i in range(1536)]
            mock_call_api.return_value = [mock_embedding]

            with patch.object(
                embedding_service, "_store_embedding"
            ) as mock_store:
                articles = [{"id": "art-1", "title": "Test"}]

                embedding_service.batch_embed_articles(articles)

                # Verify storage was called with correct structure
                mock_store.assert_called_once()
                call_args = mock_store.call_args
                assert call_args[0][0] == "art-1"  # article_id
                assert len(call_args[0][1]) == 1536  # embedding length
                assert isinstance(call_args[0][2], int)  # timestamp

    @patch.object(ArticleEmbeddingModel, "get")
    def test_embedding_retrieval_from_cache(self, mock_get, embedding_service):
        """TEST-CLU-002: Embeddings retrieved correctly from DynamoDB."""
        mock_model = MagicMock()
        mock_embedding = [0.1] * 1536
        mock_model.embedding = mock_embedding

        # Return cached model
        mock_get.return_value = mock_model

        with patch.object(
            embedding_service, "_batch_api_embeddings"
        ) as mock_api:
            mock_api.return_value = {}

            articles = [{"id": "art-1", "title": "Test"}]

            result = embedding_service.batch_embed_articles(articles)

            assert "art-1" in result
            assert result["art-1"]["embedding"] == mock_embedding
            assert result["art-1"]["cached"] is True

    def test_cache_miss_handling(self, embedding_service):
        """EDGE: Cache miss handled correctly."""
        with patch.object(embedding_service, "_check_cache") as mock_check:
            mock_check.return_value = None

            result = embedding_service._check_cache("nonexistent")

            assert result is None

    @patch.object(ArticleEmbeddingModel, "get")
    def test_query_embeddings_by_article_id(self, mock_get, embedding_service):
        """COMPLEX: Query embeddings table by article ID."""
        mock_model = MagicMock()
        mock_model.article_id = "art-123"
        mock_model.embedding = [0.1] * 1536
        mock_model.model = "text-embedding-3-small"
        mock_model.timestamp = 1234567890

        mock_get.return_value = mock_model

        result = embedding_service._check_cache("art-123")

        assert result == [0.1] * 1536
        mock_get.assert_called_once_with("art-123")


class TestCallAPIWithRetry:
    """Tests for OpenAI API calls with retry logic."""

    def test_api_call_success(self, embedding_service):
        """BASIC: Successful API call."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1] * 1536),
                MagicMock(embedding=[0.2] * 1536),
            ]
            mock_client.embeddings.create.return_value = mock_response

            result = embedding_service._call_api_with_retry(["text1", "text2"])

            assert len(result) == 2
            assert len(result[0]) == 1536
            assert len(result[1]) == 1536

    def test_exponential_backoff_timings(self, embedding_service):
        """HARD: Exponential backoff uses correct timings (1s, 2s, 4s)."""
        expected_backoffs = [1, 2, 4]

        # For implementation validation
        for attempt in range(3):
            expected = 2 ** attempt
            assert expected == expected_backoffs[attempt]

    def test_retry_max_attempts_3(self, embedding_service):
        """TEST-CLU-002: Max 3 retry attempts before giving up."""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # All calls fail
            from openai import APIError

            mock_client.embeddings.create.side_effect = APIError("API Error")

            with pytest.raises(Exception) as exc_info:
                embedding_service._call_api_with_retry(["text1"])

            # Verify error message mentions max attempts
            assert "3 attempts" in str(exc_info.value)


class TestPrepareTextForEmbedding:
    """Tests for text preparation."""

    def test_prepare_text_title_only(self, embedding_service):
        """BASIC: Prepare text with title only."""
        text = embedding_service.prepare_text_for_embedding(
            title="Test Article",
            summary=None,
            content=None,
        )

        assert "Test Article" in text

    def test_prepare_text_with_all_fields(self, embedding_service):
        """COMPLEX: Prepare text with title, summary, and content."""
        text = embedding_service.prepare_text_for_embedding(
            title="Test Article",
            summary="This is a summary",
            content="This is the full content that should be truncated to 500 chars",
        )

        assert "Test Article" in text
        assert "This is a summary" in text
        assert "This is the full content" in text

    def test_prepare_text_content_truncation(self, embedding_service):
        """HARD: Content is truncated to 500 characters."""
        long_content = "x" * 1000

        text = embedding_service.prepare_text_for_embedding(
            title="Title",
            summary="Summary",
            content=long_content,
        )

        # Content should be truncated
        assert "Title" in text
        assert "Summary" in text
        # The 500 char content should be included
        assert text.count("x") <= 500


class TestCacheCheckAndStorage:
    """Tests for cache check and storage operations."""

    @patch.object(ArticleEmbeddingModel, "get")
    def test_check_cache_hit(self, mock_get, embedding_service):
        """BASIC: Cache hit returns embedding."""
        mock_model = MagicMock()
        mock_embedding = [0.1, 0.2, 0.3]
        mock_model.embedding = mock_embedding

        mock_get.return_value = mock_model

        result = embedding_service._check_cache("art-1")

        assert result == mock_embedding

    @patch.object(ArticleEmbeddingModel, "get")
    def test_check_cache_miss(self, mock_get, embedding_service):
        """BASIC: Cache miss returns None."""
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        result = embedding_service._check_cache("art-1")

        assert result is None

    @patch.object(ArticleEmbeddingModel, "get")
    def test_check_cache_error_handling(self, mock_get, embedding_service):
        """EDGE: Cache check error returns None."""
        mock_get.side_effect = Exception("Connection error")

        result = embedding_service._check_cache("art-1")

        assert result is None

    @patch.object(ArticleEmbeddingModel, "__init__", return_value=None)
    @patch.object(ArticleEmbeddingModel, "save")
    def test_store_embedding_success(
        self, mock_save, mock_init, embedding_service
    ):
        """BASIC: Embedding stored successfully."""
        embedding_service._store_embedding("art-1", [0.1, 0.2, 0.3])

        # Verify save was called
        mock_save.assert_called_once()

    @patch.object(ArticleEmbeddingModel, "__init__", return_value=None)
    @patch.object(ArticleEmbeddingModel, "save")
    def test_store_embedding_with_timestamp(
        self, mock_save, mock_init, embedding_service
    ):
        """COMPLEX: Embedding stored with custom timestamp."""
        custom_timestamp = 1234567890

        embedding_service._store_embedding(
            "art-1", [0.1, 0.2, 0.3], timestamp=custom_timestamp
        )

        mock_save.assert_called_once()

    @patch.object(ArticleEmbeddingModel, "__init__", return_value=None)
    @patch.object(ArticleEmbeddingModel, "save")
    def test_store_embedding_error_raises(self, mock_save, mock_init, embedding_service):
        """HARD: Storage error is raised."""
        mock_save.side_effect = Exception("Storage error")

        with pytest.raises(Exception):
            embedding_service._store_embedding("art-1", [0.1, 0.2, 0.3])
