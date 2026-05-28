"""
Integration tests for EmbeddingService with DynamoDB.
Tests the full embedding service lifecycle.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.services.embedding_service import EmbeddingService
from app.models.article_embedding import ArticleEmbeddingModel


@pytest.fixture
def embedding_service():
    """Create EmbeddingService."""
    service = EmbeddingService()
    service.api_key = "test-key"
    return service


class TestEmbeddingServiceIntegration:
    """Integration tests for the embedding service."""

    @patch.object(ArticleEmbeddingModel, "get")
    @patch("openai.OpenAI")
    def test_full_batch_embedding_workflow(self, mock_openai, mock_get, embedding_service):
        """
        TEST-CLU-002: Full batch embedding workflow.
        Simulates complete flow: cache check -> API call -> storage.
        """
        # Setup: First 5 articles cached, next 5 need API calls
        def get_side_effect(article_id):
            article_num = int(article_id.split("-")[1])
            if article_num < 5:
                mock_model = MagicMock()
                mock_model.embedding = [0.1] * 1536
                return mock_model
            raise ArticleEmbeddingModel.DoesNotExist()

        mock_get.side_effect = get_side_effect

        # Setup OpenAI mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.2] * 1536) for _ in range(5)
        ]
        mock_client.embeddings.create.return_value = mock_response

        with patch.object(embedding_service, "_store_embedding") as mock_store:
            articles = [
                {"id": f"art-{i}", "title": f"Title {i}"} for i in range(10)
            ]

            result = embedding_service.batch_embed_articles(articles)

            # Verify results
            assert len(result) == 10

            # 5 should be cached
            cached_count = sum(
                1 for r in result.values() if r.get("cached", False)
            )
            assert cached_count == 5

            # 5 should be from API
            api_count = sum(
                1 for r in result.values() if not r.get("cached", False)
            )
            assert api_count == 5

            # Storage should be called for new embeddings
            assert mock_store.call_count == 5

            # Verify API was called
            mock_client.embeddings.create.assert_called_once()

    @patch.object(ArticleEmbeddingModel, "get")
    @patch("openai.OpenAI")
    def test_batch_split_across_250_articles(self, mock_openai, mock_get, embedding_service):
        """
        TEST-CLU-002: Batch efficiency with 250 articles.
        Should make 3 API calls (100+100+50).
        """
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        def api_side_effect(input, model, dimensions):
            # Return correct number of embeddings
            num_texts = len(input)
            return MagicMock(
                data=[
                    MagicMock(embedding=[0.1] * 1536) for _ in range(num_texts)
                ]
            )

        mock_client.embeddings.create.side_effect = api_side_effect

        with patch.object(embedding_service, "_store_embedding"):
            articles = [
                {"id": f"art-{i}", "title": f"Title {i}"} for i in range(250)
            ]

            result = embedding_service.batch_embed_articles(articles)

            assert len(result) == 250

            # Verify 3 API calls
            assert mock_client.embeddings.create.call_count == 3

            # Verify batch sizes
            calls = mock_client.embeddings.create.call_args_list
            batch_1_size = len(calls[0][1]["input"])
            batch_2_size = len(calls[1][1]["input"])
            batch_3_size = len(calls[2][1]["input"])

            assert batch_1_size == 100
            assert batch_2_size == 100
            assert batch_3_size == 50

    @patch.object(ArticleEmbeddingModel, "get")
    @patch("openai.OpenAI")
    def test_retry_mechanism_on_api_failure(self, mock_openai, mock_get, embedding_service):
        """
        TEST-CLU-002: Retry mechanism with exponential backoff.
        """
        mock_get.side_effect = ArticleEmbeddingModel.DoesNotExist()

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Fail twice, succeed on third attempt
        from openai import APIError

        attempts = [0]

        def create_side_effect(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] < 3:
                raise APIError("Temporary error")
            return MagicMock(
                data=[MagicMock(embedding=[0.1] * 1536)]
            )

        mock_client.embeddings.create.side_effect = create_side_effect

        with patch.object(embedding_service, "_store_embedding"):
            articles = [{"id": "art-1", "title": "Test"}]

            # Should succeed after retries
            result = embedding_service.batch_embed_articles(articles)

            assert len(result) == 1
            assert "art-1" in result

    @patch.object(ArticleEmbeddingModel, "get")
    def test_empty_articles_list(self, mock_get, embedding_service):
        """EDGE: Empty articles list returns empty dict."""
        result = embedding_service.batch_embed_articles([])

        assert result == {}
        mock_get.assert_not_called()

    @patch.object(ArticleEmbeddingModel, "get")
    def test_mixed_cached_and_new_articles(self, mock_get, embedding_service):
        """COMPLEX: Mix of cached and new articles."""
        def get_side_effect(article_id):
            if article_id in ["art-1", "art-3", "art-5"]:
                mock_model = MagicMock()
                mock_model.embedding = [0.1] * 1536
                return mock_model
            raise ArticleEmbeddingModel.DoesNotExist()

        mock_get.side_effect = get_side_effect

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.2] * 1536) for _ in range(3)
            ]
            mock_client.embeddings.create.return_value = mock_response

            with patch.object(embedding_service, "_store_embedding"):
                articles = [
                    {"id": f"art-{i}", "title": f"Title {i}"} for i in range(1, 6)
                ]

                result = embedding_service.batch_embed_articles(articles)

                assert len(result) == 5

                # Check cached and new
                assert result["art-1"]["cached"] is True
                assert result["art-2"]["cached"] is False
                assert result["art-3"]["cached"] is True
                assert result["art-4"]["cached"] is False
                assert result["art-5"]["cached"] is True


class TestArticleEmbeddingModel:
    """Tests for ArticleEmbeddingModel."""

    @patch.object(ArticleEmbeddingModel, "__init__", return_value=None)
    @patch.object(ArticleEmbeddingModel, "save")
    def test_model_creation(self, mock_save, mock_init, embedding_service):
        """BASIC: Model creation works correctly."""
        embedding_service._store_embedding(
            "art-1", [0.1, 0.2, 0.3], timestamp=1234567890
        )

        mock_save.assert_called_once()

    @patch.object(ArticleEmbeddingModel, "get")
    def test_model_retrieval(self, mock_get, embedding_service):
        """BASIC: Model retrieval works correctly."""
        mock_model = MagicMock()
        mock_model.embedding = [0.1, 0.2, 0.3]
        mock_get.return_value = mock_model

        result = embedding_service._check_cache("art-1")

        assert result == [0.1, 0.2, 0.3]
        mock_get.assert_called_once_with("art-1")
