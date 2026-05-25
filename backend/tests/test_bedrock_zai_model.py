"""Tests for Bedrock ZAI GLM 4.7 Flash model integration."""

import pytest
import json
from io import BytesIO
from unittest.mock import AsyncMock, patch, MagicMock

from app.integrations.llm_client import BedrockClient


class TestBedrockZaiGLMModel:
    """Tests for AWS Bedrock with zai.glm-4.7-flash model."""

    @pytest.fixture
    def client(self):
        """Create Bedrock client with zai.glm-4.7-flash model."""
        with patch("boto3.client"):
            return BedrockClient(region="us-west-2", model="zai.glm-4.7-flash")

    @pytest.mark.asyncio
    async def test_generate_with_zai_model(self, client):
        """Test text generation with zai.glm-4.7-flash model."""
        # Mock the boto3 invoke_model response
        response_body = {
            "content": [
                {
                    "type": "text",
                    "text": "This is a response from zai.glm-4.7-flash model"
                }
            ],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 15
            }
        }

        mock_response = MagicMock()
        mock_response["body"].read.return_value = json.dumps(response_body).encode()

        with patch.object(client.client, "invoke_model", return_value=mock_response):
            result = await client.generate("Test prompt")
            assert result == "This is a response from zai.glm-4.7-flash model"

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(self, client):
        """Test generation with custom temperature and max_tokens."""
        response_body = {
            "content": [
                {
                    "type": "text",
                    "text": "Custom response"
                }
            ],
            "stop_reason": "end_turn"
        }

        mock_response = MagicMock()
        mock_response["body"].read.return_value = json.dumps(response_body).encode()

        with patch.object(client.client, "invoke_model", return_value=mock_response) as mock_invoke:
            result = await client.generate(
                "Test prompt",
                max_tokens=500,
                temperature=0.3
            )

            assert result == "Custom response"
            # Verify invoke_model was called with correct parameters
            assert mock_invoke.called
            call_args = mock_invoke.call_args
            assert call_args[1]["modelId"] == "zai.glm-4.7-flash"

    @pytest.mark.asyncio
    async def test_generate_json_response(self, client):
        """Test generation of JSON responses."""
        response_body = {
            "content": [
                {
                    "type": "text",
                    "text": '{"score": 8.5, "reasoning": "High quality content"}'
                }
            ],
            "stop_reason": "end_turn"
        }

        mock_response = MagicMock()
        mock_response["body"].read.return_value = json.dumps(response_body).encode()

        with patch.object(client.client, "invoke_model", return_value=mock_response):
            result = await client.generate("Evaluate this article")
            parsed = json.loads(result)
            assert parsed["score"] == 8.5
            assert parsed["reasoning"] == "High quality content"

    @pytest.mark.asyncio
    async def test_error_handling_missing_content(self, client):
        """Test error handling when response is missing content field."""
        response_body = {
            "error": "Invalid request"
        }

        mock_response = MagicMock()
        mock_response["body"].read.return_value = json.dumps(response_body).encode()

        with patch.object(client.client, "invoke_model", return_value=mock_response):
            with pytest.raises(KeyError) as exc_info:
                await client.generate("Test prompt")
            assert "content" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_empty_content(self, client):
        """Test error handling when content list is empty."""
        response_body = {
            "content": [],
            "stop_reason": "end_turn"
        }

        mock_response = MagicMock()
        mock_response["body"].read.return_value = json.dumps(response_body).encode()

        with patch.object(client.client, "invoke_model", return_value=mock_response):
            with pytest.raises((ValueError, IndexError)):
                await client.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_health_check_zai_model(self, client):
        """Test health check for zai.glm-4.7-flash model."""
        with patch.object(client.client, "list_foundation_models", return_value={"modelSummaries": []}):
            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check when Bedrock is unavailable."""
        with patch.object(client.client, "list_foundation_models", side_effect=Exception("AWS error")):
            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_model_id_in_payload(self, client):
        """Test that zai.glm-4.7-flash model ID is correctly sent in payload."""
        response_body = {
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn"
        }

        mock_response = MagicMock()
        mock_response["body"].read.return_value = json.dumps(response_body).encode()

        with patch.object(client.client, "invoke_model", return_value=mock_response) as mock_invoke:
            await client.generate("Test")

            # Check that the model ID is correct
            call_kwargs = mock_invoke.call_args[1]
            assert call_kwargs["modelId"] == "zai.glm-4.7-flash"
            assert call_kwargs["contentType"] == "application/json"
            assert call_kwargs["accept"] == "application/json"

            # Check the payload has correct structure
            payload = json.loads(call_kwargs["body"])
            assert payload["anthropic_version"] == "bedrock-2023-05-31"
            assert "messages" in payload
            assert "max_tokens" in payload
            assert "temperature" in payload

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test handling multiple concurrent requests."""
        import asyncio

        response_body = {
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn"
        }

        mock_response = MagicMock()
        mock_response["body"].read.return_value = json.dumps(response_body).encode()

        with patch.object(client.client, "invoke_model", return_value=mock_response):
            # Run 3 concurrent requests
            results = await asyncio.gather(
                client.generate("Prompt 1"),
                client.generate("Prompt 2"),
                client.generate("Prompt 3"),
            )

            assert len(results) == 3
            assert all(r == "Response" for r in results)
