"""Tests for LLM client supporting multiple providers."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.integrations.llm_client import (
    LLMClient,
    OpenAIClient,
    GeminiClient,
    BedrockClient,
    OllamaClient,
)


class TestOpenAIClient:
    """Tests for OpenAI LLM client."""

    @pytest.fixture
    def client(self):
        """Create OpenAI client."""
        return OpenAIClient(api_key="test-key", model="gpt-4o-mini")

    @pytest.mark.asyncio
    async def test_generate_basic_success(self, client):
        """Test basic text generation."""
        with patch("app.integrations.llm_client.httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test response"}}]
            }
            mock_post.return_value = mock_response

            result = await client.generate("Test prompt")
            assert result == "Test response"
            assert mock_post.called

    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, client):
        """Test generation with custom parameters."""
        with patch("app.integrations.llm_client.httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Short response"}}]
            }
            mock_post.return_value = mock_response

            result = await client.generate("Test", max_tokens=100, temperature=0.5)
            assert result == "Short response"

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check when API is available."""
        with patch("app.integrations.llm_client.httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check when API is unavailable."""
        with patch("app.integrations.llm_client.httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await client.health_check()
            assert result is False


class TestGeminiClient:
    """Tests for Gemini LLM client."""

    @pytest.fixture
    def client(self):
        """Create Gemini client."""
        return GeminiClient(api_key="test-key", model="gemini-1.5-mini")

    @pytest.mark.asyncio
    async def test_generate_basic_success(self, client):
        """Test Gemini text generation."""
        with patch("app.integrations.llm_client.httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}]
            }
            mock_post.return_value = mock_response

            result = await client.generate("Test prompt")
            assert result == "Gemini response"


@pytest.mark.skip(reason="Bedrock is optional provider")
class TestBedrockClient:
    """Tests for AWS Bedrock LLM client."""

    @pytest.mark.asyncio
    async def test_bedrock_requires_boto3(self):
        """Test that Bedrock requires boto3."""
        with patch("app.integrations.llm_client.boto3", side_effect=ImportError):
            with pytest.raises(ImportError):
                BedrockClient(region="us-east-1", model="claude-3")


class TestOllamaClient:
    """Tests for Ollama local LLM client."""

    @pytest.fixture
    def client(self):
        """Create Ollama client."""
        return OllamaClient(base_url="http://localhost:11434", model="llama2")

    @pytest.mark.asyncio
    async def test_generate_local_success(self, client):
        """Test local Ollama generation."""
        with patch("app.integrations.llm_client.httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Ollama response"}
            mock_post.return_value = mock_response

            result = await client.generate("Test prompt")
            assert result == "Ollama response"

    @pytest.mark.asyncio
    async def test_health_check_local(self, client):
        """Test Ollama health check."""
        with patch("app.integrations.llm_client.httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = await client.health_check()
            assert result is True


class TestLLMClientFactory:
    """Tests for LLM client factory."""

    @pytest.mark.asyncio
    async def test_factory_creates_openai_client(self):
        """Test factory creates OpenAI client."""
        with patch("app.integrations.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_model = "gpt-4o-mini"

            client = LLMClient()
            assert isinstance(client.primary_provider, OpenAIClient)

    @pytest.mark.asyncio
    async def test_factory_creates_gemini_client(self):
        """Test factory creates Gemini client."""
        with patch("app.integrations.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-1.5-mini"

            client = LLMClient()
            assert isinstance(client.primary_provider, GeminiClient)

    @pytest.mark.asyncio
    async def test_factory_creates_ollama_client(self):
        """Test factory creates Ollama client."""
        with patch("app.integrations.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_base_url = "http://localhost:11434"
            mock_settings.ollama_model = "llama2"

            client = LLMClient()
            assert isinstance(client.primary_provider, OllamaClient)

    @pytest.mark.asyncio
    async def test_factory_raises_on_unsupported_provider(self):
        """Test factory raises error for unsupported provider."""
        with patch("app.integrations.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "unsupported"

            with pytest.raises(ValueError):
                LLMClient()

    @pytest.mark.asyncio
    async def test_factory_raises_without_api_key(self):
        """Test factory raises error without required API key."""
        with patch("app.integrations.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = None

            with pytest.raises(ValueError):
                LLMClient()
