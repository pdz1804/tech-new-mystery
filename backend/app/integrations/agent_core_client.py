"""Agent Core Client for HTTP API integration."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AgentCoreClient:
    """Client for Agent Core HTTP API with streaming support."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        """Initialize Agent Core client.

        Args:
            base_url: Base URL for Agent Core API (defaults to settings)
            api_key: API key for authentication (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = (base_url or settings.agent_core_base_url).rstrip("/")
        self.api_key = api_key or settings.agent_core_api_key
        self.timeout = timeout or settings.agent_core_timeout

        # Create async HTTP client with connection pooling
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def invoke_agent(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Invoke Agent Core with streaming response.

        Args:
            session_id: Unique session identifier
            user_message: User's input message
            context: Optional context dictionary
            user_id: Optional user identifier

        Yields:
            Dict with event data (token, tool_invocation, tool_result, done, error)

        Raises:
            httpx.TimeoutException: If request times out
            httpx.HTTPError: If HTTP error occurs
        """
        url = f"{self.base_url}/agent/invoke"
        headers = self._get_headers()

        payload = {
            "session_id": session_id,
            "user_message": user_message,
            "context": context or {},
            "user_id": user_id,
        }

        try:
            async with self._client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
            ) as response:
                # Check for HTTP errors
                response.raise_for_status()

                # Stream and parse events
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        event = json.loads(line)
                        yield event
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse event JSON: {e}, line: {line}")
                        yield {"type": "error", "message": f"JSON parse error: {e}"}

        except httpx.TimeoutException as e:
            logger.error(f"Agent Core timeout: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Agent Core HTTP error: {e}")
            raise

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/x-ndjson",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
