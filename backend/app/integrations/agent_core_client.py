"""Agent Core Client for HTTP/SSE runtime integration."""

import json
import logging
import time
from enum import Enum
from typing import AsyncGenerator, Dict, Any, Iterable

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast - Agent Core down
    HALF_OPEN = "half_open" # Testing if Agent Core recovered


class AgentCoreCircuitBreaker:
    """Circuit breaker for Agent Core calls.

    Opens after 5 consecutive failures, resets after 30s cooldown.
    """

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 30.0  # seconds before trying again

    def __init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self._opened_at: float = 0.0

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                f"[CIRCUIT] Opened after {self.failure_count} consecutive failures"
            )

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self.RECOVERY_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                logger.info("[CIRCUIT] Half-open — probing Agent Core")
                return True
            return False
        # HALF_OPEN: allow exactly one probe
        return True

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN


# Module-level singleton so all requests share state
_circuit_breaker = AgentCoreCircuitBreaker()


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
        """Invoke Agent Core with a streaming HTTP/SSE response.

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
        url = f"{self.base_url}/invocations"
        headers = self._get_headers()

        payload = {
            "prompt": user_message,
            "session_id": session_id,
            "context": context or {},
        }

        if not _circuit_breaker.allow_request():
            logger.warning("[CIRCUIT] Agent Core circuit open — failing fast")
            raise ConnectionError(
                "Agent Core is currently unavailable (circuit open). "
                f"Retry after {AgentCoreCircuitBreaker.RECOVERY_TIMEOUT}s."
            )

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
                async for event in self._iter_stream_events(response):
                    yield event

            _circuit_breaker.record_success()

        except httpx.TimeoutException as e:
            _circuit_breaker.record_failure()
            logger.error(f"Agent Core timeout: {e}")
            raise
        except httpx.HTTPError as e:
            _circuit_breaker.record_failure()
            logger.error(f"Agent Core HTTP error: {e}")
            raise
        except ConnectionError:
            raise  # Already logged above, don't count as new failure
        except Exception as e:
            _circuit_breaker.record_failure()
            raise

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/x-ndjson",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    async def _iter_stream_events(
        self,
        response: httpx.Response,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Parse Agent Core streaming responses.

        The runtime should stream SSE, but accepting newline-delimited JSON keeps
        the client tolerant of local harnesses and older Agent Core builds.
        """
        sse_event_name: str | None = None
        sse_data_lines: list[str] = []

        async for raw_line in response.aiter_lines():
            line = raw_line.rstrip("\r")

            if not line:
                if sse_data_lines:
                    event = self._parse_sse_event(sse_event_name, sse_data_lines)
                    sse_event_name = None
                    sse_data_lines = []
                    if event:
                        yield event
                continue

            if line.startswith(":"):
                continue

            if line.startswith("event:"):
                sse_event_name = line.removeprefix("event:").strip()
                continue

            if line.startswith("data:"):
                sse_data_lines.append(line.removeprefix("data:").lstrip())
                continue

            if line.startswith(("id:", "retry:")):
                continue

            if sse_data_lines:
                sse_data_lines.append(line)
                continue

            event = self._parse_json_event(line)
            if event:
                yield event

        if sse_data_lines:
            event = self._parse_sse_event(sse_event_name, sse_data_lines)
            if event:
                yield event

    def _parse_sse_event(
        self,
        event_name: str | None,
        data_lines: Iterable[str],
    ) -> Dict[str, Any] | None:
        data = "\n".join(data_lines).strip()
        if not data or data == "[DONE]":
            return {"type": "done"} if data == "[DONE]" else None

        event = self._parse_json_event(data, default_type=event_name or "message")
        if event is None:
            return {
                "type": "error",
                "message": "Agent Core returned malformed SSE data",
            }
        return event

    def _parse_json_event(
        self,
        payload: str,
        default_type: str = "message",
    ) -> Dict[str, Any] | None:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event JSON: {e}, payload: {payload}")
            return {"type": "error", "message": f"JSON parse error: {e}"}

        if not isinstance(event, dict):
            return {
                "type": "error",
                "message": "Agent Core event payload must be a JSON object",
            }

        if "type" not in event:
            # Handle BedrockAgentCoreApp native format: {"response": "...", "status": "success|error"}
            if "response" in event:
                if event.get("status") == "error":
                    return {"type": "error", "message": str(event.get("response", "Unknown agent error"))}
                return {"type": "token", "content": str(event["response"])}
            event["type"] = default_type
        return event

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
