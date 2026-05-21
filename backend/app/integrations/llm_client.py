"""Multi-provider LLM client supporting OpenAI, Gemini, Bedrock, Ollama, and Claude."""

import json
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available."""
        pass


class OpenAIClient(LLMProvider):
    """OpenAI API client."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> str:
        """Generate text using OpenAI API."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def health_check(self) -> bool:
        """Check OpenAI API availability."""
        try:
            response = await self.client.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class GeminiClient(LLMProvider):
    """Google Gemini API client."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> str:
        """Generate text using Gemini API."""
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        response = await self.client.post(
            f"{self.base_url}/{self.model}:generateContent?key={self.api_key}",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def health_check(self) -> bool:
        """Check Gemini API availability."""
        try:
            response = await self.client.get(
                f"{self.base_url}?key={self.api_key}",
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class BedrockClient(LLMProvider):
    """AWS Bedrock API client."""

    def __init__(self, region: str, model: str):
        self.region = region
        self.model = model
        try:
            import boto3
            from botocore.config import Config

            bedrock_config = Config(
                read_timeout=30,
                connect_timeout=10,
                retries={"max_attempts": 1},
            )
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=region,
                config=bedrock_config,
            )
        except ImportError:
            raise ImportError("boto3 is required for Bedrock support")

    async def generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> str:
        """Generate text using Bedrock API."""
        import asyncio

        payload = {
            "anthropic_version": "bedrock-2023-06-01",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
        }

        async def _invoke():
            def sync_invoke():
                return self.client.invoke_model(
                    modelId=self.model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload),
                )
            return await asyncio.to_thread(sync_invoke)

        response = await _invoke()
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    async def health_check(self) -> bool:
        """Check Bedrock availability."""
        import asyncio

        async def _check():
            def sync_check():
                return self.client.list_foundation_models()
            return await asyncio.to_thread(sync_check)

        try:
            await _check()
            return True
        except Exception:
            return False


class OllamaClient(LLMProvider):
    """Local Ollama API client."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> str:
        """Generate text using Ollama API."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["response"]

    async def health_check(self) -> bool:
        """Check Ollama availability."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class LLMClient:
    """Multi-provider LLM client with fallback support."""

    def __init__(self):
        self.providers = self._init_providers()
        self.primary_provider = self.providers[0] if self.providers else None

    def _init_providers(self) -> list[LLMProvider]:
        """Initialize LLM providers with fallback chain."""
        providers = []
        provider_chain = settings.llm_provider.lower().split(",")

        for provider_type in provider_chain:
            provider_type = provider_type.strip()

            try:
                if provider_type == "openai":
                    if settings.openai_api_key:
                        providers.append(OpenAIClient(settings.openai_api_key, settings.openai_model))
                elif provider_type == "gemini":
                    if settings.gemini_api_key:
                        providers.append(GeminiClient(settings.gemini_api_key, settings.gemini_model))
                elif provider_type == "bedrock":
                    if settings.bedrock_region:
                        providers.append(BedrockClient(settings.bedrock_region, settings.bedrock_model))
                elif provider_type == "ollama":
                    providers.append(OllamaClient(settings.ollama_base_url, settings.ollama_model))
            except Exception as e:
                # Skip providers that fail to initialize
                continue

        if not providers:
            raise ValueError("No LLM providers could be initialized")
        return providers

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using configured providers with fallback."""
        import logging

        logger = logging.getLogger(__name__)
        last_error = None
        for i, provider in enumerate(self.providers):
            provider_name = provider.__class__.__name__
            try:
                logger.debug(f"Attempting LLM generation with {provider_name}")
                result = await provider.generate(prompt, max_tokens, temperature)
                logger.info(f"Successfully generated with {provider_name}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    f"{provider_name} failed (attempt {i + 1}/{len(self.providers)}): "
                    f"{type(e).__name__}: {str(e)}"
                )
                if i < len(self.providers) - 1:
                    logger.info(f"Falling back to next provider...")
                    continue
                else:
                    logger.error(f"All LLM providers exhausted. Last error: {str(last_error)}")
                    raise last_error

    async def health_check(self) -> bool:
        """Check if any LLM provider is available."""
        for provider in self.providers:
            try:
                if await provider.health_check():
                    return True
            except Exception:
                continue
        return False

    async def close(self):
        """Close provider connections."""
        for provider in self.providers:
            if hasattr(provider, "close"):
                await provider.close()


# Singleton instance
_llm_client: Optional[LLMClient] = None


async def get_llm_client() -> LLMClient:
    """Get or create LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def shutdown_llm():
    """Shutdown LLM client."""
    global _llm_client
    if _llm_client:
        await _llm_client.close()
        _llm_client = None
