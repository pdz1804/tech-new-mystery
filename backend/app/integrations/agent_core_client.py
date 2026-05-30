"""AWS Bedrock AgentCore Runtime client.

Production:  uses boto3 bedrock-agentcore.invoke_agent_runtime()
             configured via AGENT_CORE_RUNTIME_ARN env var.

Local dev:   falls back to direct HTTP POST to /invocations
             configured via AGENT_CORE_BASE_URL env var (e.g. http://localhost:8080).

Both paths emit the same yielded dict schema:
  {"type": "token",           "content": "..."}
  {"type": "tool_invocation", "tool_name": "...", "tool_id": "...", "tool_args": {...}}
  {"type": "tool_result",     "tool_name": "...", "status": "completed|failed", "result_summary": "..."}
  {"type": "done"}
  {"type": "error",           "message": "...", "recoverable": True|False}
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import re
import threading
import time
from enum import Enum
from typing import AsyncGenerator, Dict, Any, Iterable

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_STREAM_CHUNK_WORDS = 4
FALLBACK_STREAM_DELAY_SECONDS = 0.05


# ---------------------------------------------------------------------------
# Circuit breaker (shared across all client instances)
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AgentCoreCircuitBreaker:
    """Circuit breaker for AgentCore Runtime calls.

    No threading.Lock is needed here: this object is only ever accessed from
    async coroutines running on the asyncio event loop (a single OS thread).
    Coroutines interleave exclusively at 'await' points, and none of these
    methods contain any 'await', so each method runs to completion atomically
    within one event loop tick — no concurrent modification is possible.
    """

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 30.0

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
            logger.warning("[CIRCUIT] Opened after %d failures", self.failure_count)

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self.RECOVERY_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                logger.info("[CIRCUIT] Half-open — probing agent")
                return True
            return False
        return True

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN


_circuit_breaker = AgentCoreCircuitBreaker()


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class AgentCoreClient:
    """Invoke the AgentCore Runtime and stream back events.

    Priority:
      1. If settings.agent_core_runtime_arn is set → boto3 invoke_agent_runtime
      2. Else if settings.agent_core_base_url is set → HTTP POST /invocations
    """

    def __init__(self) -> None:
        self._runtime_arn: str | None = getattr(settings, "agent_core_runtime_arn", None)
        self._base_url: str | None = getattr(settings, "agent_core_base_url", None)
        self._api_key: str | None = getattr(settings, "agent_core_api_key", None)
        self._timeout: int = getattr(settings, "agent_core_timeout", 60)
        self._http_client: httpx.AsyncClient | None = None

        if self._runtime_arn:
            import boto3
            self._boto3_client = boto3.client(
                "bedrock-agentcore",
                region_name=getattr(settings, "aws_region", "us-west-2"),
            )
            logger.debug("[AGENTCORE] Using boto3 invoke_agent_runtime: %s", self._runtime_arn)
        elif self._base_url:
            # Per-request client for SSE streaming.
            # A shared pool with fixed max_connections silently queues the N+1th user;
            # per-request avoids that. read=None is required — httpx's read timeout fires
            # between chunks and breaks long-running SSE streams.
            # Overall 60s wall-clock limit is enforced by _iterate_with_timeout in the router.
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=None,   # no per-chunk timeout — router handles wall-clock limit
                    write=10.0,
                    pool=5.0,
                ),
            )
            logger.debug("[AGENTCORE] Using HTTP fallback: %s", self._base_url)
        else:
            logger.warning("[AGENTCORE] No AGENT_CORE_RUNTIME_ARN or AGENT_CORE_BASE_URL configured")

    async def invoke_agent(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream events from the AgentCore Runtime."""
        if not _circuit_breaker.allow_request():
            logger.warning("[CIRCUIT] Agent Core circuit open — failing fast")
            raise ConnectionError("Agent Core unavailable (circuit open)")

        try:
            if self._runtime_arn:
                async for event in self._invoke_via_boto3(session_id, user_message, context, user_id):
                    yield event
            elif self._base_url:
                async for event in self._invoke_via_http(session_id, user_message, context, user_id):
                    yield event
            else:
                yield {"type": "error", "message": "Agent Core not configured", "recoverable": False}
                return

            _circuit_breaker.record_success()

        except ConnectionError:
            raise
        except Exception as exc:
            _circuit_breaker.record_failure()
            raise

    # ------------------------------------------------------------------
    # boto3 path (production — AWS Bedrock AgentCore Runtime)
    # ------------------------------------------------------------------

    async def _invoke_via_boto3(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any] | None,
        user_id: str | None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        payload = json.dumps({
            "prompt": user_message,
            "session_id": session_id,
            "user_id": user_id or "anonymous",
            "context": context or {},
        }).encode()

        # boto3 call is synchronous — run in thread pool
        response = await asyncio.to_thread(
            self._boto3_client.invoke_agent_runtime,
            agentRuntimeArn=self._runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
        )

        # Stream response body via a thread/queue bridge (iter_lines is synchronous)
        line_queue: queue.Queue = queue.Queue()

        def _stream_lines():
            try:
                streaming_body = response.get("response")
                if streaming_body:
                    for line in streaming_body.iter_lines(chunk_size=32):
                        line_queue.put(line)
            except Exception as exc:
                line_queue.put(exc)
            finally:
                line_queue.put(None)

        thread = threading.Thread(target=_stream_lines, daemon=True)
        thread.start()

        loop = asyncio.get_event_loop()
        sse_event_name: str | None = None
        sse_data_lines: list[str] = []

        while True:
            raw = await loop.run_in_executor(None, line_queue.get)
            if raw is None:
                break
            if isinstance(raw, Exception):
                raise raw

            line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            line = line.rstrip("\r")

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

            # NDJSON fallback
            event = self._parse_json_event(line)
            if event:
                yield event

        if sse_data_lines:
            event = self._parse_sse_event(sse_event_name, sse_data_lines)
            if event:
                yield event

    # ------------------------------------------------------------------
    # HTTP path (local dev — BedrockAgentCoreApp running on localhost)
    # ------------------------------------------------------------------

    async def _invoke_via_http(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any] | None,
        user_id: str | None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        url = f"{self._base_url.rstrip('/')}/invocations"
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream, application/x-ndjson"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key

        payload = {
            "prompt": user_message,
            "session_id": session_id,
            "user_id": user_id or "anonymous",
            "context": context or {},
        }

        async with self._http_client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()

            # Check Content-Type to determine response format
            content_type = response.headers.get("content-type", "").lower()
            logger.info(f"[AGENTCORE] Response Content-Type: {content_type}")

            if "event-stream" in content_type or "ndjson" in content_type:
                # SSE or NDJSON stream
                logger.info("[AGENTCORE] Detected SSE/NDJSON stream, using _iter_sse_lines")
                event_count = 0
                async for event in self._iter_sse_lines(response):
                    event_count += 1
                    logger.debug(f"[AGENTCORE] Yielding event #{event_count}: type={event.get('type')}, content_len={len(str(event.get('content', '')))}")
                    yield event
                logger.info(f"[AGENTCORE] Total events yielded: {event_count}")
            else:
                # Plain JSON response — read and tokenize
                logger.info("[AGENTCORE] Detected JSON response, reading full body and tokenizing")
                try:
                    full_response = await response.aread()
                    logger.debug(f"[AGENTCORE] Read {len(full_response)} bytes from response")
                    json_data = json.loads(full_response.decode("utf-8"))
                    logger.debug(f"[AGENTCORE] Parsed JSON with keys: {list(json_data.keys())}")
                    async for event in self._tokenize_response(json_data):
                        yield event
                except Exception as exc:
                    logger.error("[AGENTCORE] Failed to parse JSON response: %s", exc)
                    yield {"type": "error", "message": str(exc), "recoverable": True}

    async def _tokenize_response(
        self, json_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Convert non-streaming Agent Core response into token events.

        Handles responses with structure:
        {
          "output": {
            "message": {
              "content": [{"text": "..."}, ...],
              "role": "assistant"
            }
          },
          "stopReason": "end_turn",
          "usage": {...}
        }
        """
        if getattr(settings, "agent_core_require_true_streaming", True):
            logger.error(
                "[AGENTCORE] Refusing to synthesize stream from complete JSON response "
                "because AGENT_CORE_REQUIRE_TRUE_STREAMING is enabled"
            )
            yield {
                "type": "error",
                "error_code": "TRUE_STREAMING_REQUIRED",
                "message": (
                    "Agent Core returned a complete JSON response instead of SSE/NDJSON. "
                    "Synthetic streaming is disabled."
                ),
                "recoverable": False,
            }
            return

        try:
            logger.debug(f"[AGENTCORE] Tokenizing response structure: {list(json_data.keys())}")

            # Extract message content from Agent Core response structure
            output = json_data.get("output", {})
            message = output.get("message", {})
            content_list = message.get("content", [])

            logger.debug(f"[AGENTCORE] Extracted content_list: {content_list}")

            # Collect all text from content list
            full_text = ""
            for item in content_list:
                if isinstance(item, dict) and "text" in item:
                    full_text += item["text"]

            logger.debug(f"[AGENTCORE] Extracted full_text length: {len(full_text)} chars")

            if full_text:
                async for event in self._paced_token_events(full_text):
                    yield event

            # Final done event
            yield {
                "type": "done",
                "message_id": None,
                "tokens": json_data.get("usage", {}).get("totalTokens", 0),
            }

        except Exception as exc:
            logger.error("[AGENTCORE] Failed to tokenize response: %s", exc)
            yield {"type": "error", "message": str(exc), "recoverable": True}

    async def _paced_token_events(
        self,
        text: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Emit synthetic token events slowly enough for browsers to paint.

        This is only used when Agent Core returns a complete JSON payload instead
        of an SSE/NDJSON stream. True Bedrock/LangGraph token events pass through
        without artificial delay.
        """
        words = re.findall(r"\S+|\s+", text)
        chunk = ""

        for index, word in enumerate(words):
            chunk += word
            should_flush = (
                len(chunk.split()) >= FALLBACK_STREAM_CHUNK_WORDS
                or "\n" in word
                or index == len(words) - 1
            )
            if not should_flush:
                continue

            if chunk:
                yield {"type": "token", "content": chunk}
                chunk = ""

            if index < len(words) - 1:
                await asyncio.sleep(FALLBACK_STREAM_DELAY_SECONDS)

    async def _iter_sse_lines(self, response: httpx.Response) -> AsyncGenerator[Dict[str, Any], None]:
        """Parse SSE or JSON from response.

        Agent Core claims text/event-stream but may return plain JSON.
        This method handles both by detecting JSON and falling back to tokenization.
        """
        sse_event_name: str | None = None
        sse_data_lines: list[str] = []
        line_count = 0
        first_line = True
        all_lines = []  # Debug: capture all lines

        # Buffer to detect if this is JSON instead of SSE
        json_buffer = ""

        async for raw_line in response.aiter_lines():
            line = raw_line.rstrip("\r")
            line_count += 1
            all_lines.append(line)  # Debug

            # Detect if first line looks like JSON (starts with {)
            if first_line and line.strip().startswith("{"):
                logger.info("[AGENTCORE] Detected JSON response instead of SSE, switching to tokenization")
                # This is JSON, not SSE. Read the whole body and tokenize it.
                json_buffer = line
                # Continue reading remaining lines
                async for remaining_line in response.aiter_lines():
                    json_buffer += remaining_line
                # Parse and tokenize the complete JSON
                try:
                    json_data = json.loads(json_buffer)
                    async for event in self._tokenize_response(json_data):
                        yield event
                except json.JSONDecodeError as e:
                    logger.error(f"[AGENTCORE] Failed to parse JSON fallback: {e}")
                    yield {"type": "error", "message": str(e), "recoverable": True}
                return

            first_line = False

            if not line:
                if sse_data_lines:
                    logger.debug(f"[AGENTCORE] SSE event complete: type={sse_event_name}, lines={len(sse_data_lines)}")
                    event = self._parse_sse_event(sse_event_name, sse_data_lines)
                    sse_event_name = None
                    sse_data_lines = []
                    if event:
                        logger.debug(f"[AGENTCORE] Yielding parsed event: {event.get('type')}")
                        yield event
                continue

            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                sse_event_name = line.removeprefix("event:").strip()
                logger.debug(f"[AGENTCORE] SSE event type detected: {sse_event_name}")
                continue
            if line.startswith("data:"):
                data_content = line.removeprefix("data:").lstrip()
                sse_data_lines.append(data_content)
                logger.debug(f"[AGENTCORE] SSE data line {len(sse_data_lines)}: {data_content[:100]}")
                continue
            if line.startswith(("id:", "retry:")):
                continue

            logger.debug(f"[AGENTCORE] Attempting JSON parse on line: {line[:100]}")
            event = self._parse_json_event(line)
            if event:
                logger.debug(f"[AGENTCORE] Yielding JSON event: {event.get('type')}")
                yield event

        logger.info(f"[AGENTCORE] SSE stream ended after {line_count} lines")
        logger.debug(f"[AGENTCORE] All lines received: {all_lines}")  # Debug
        if sse_data_lines:
            event = self._parse_sse_event(sse_event_name, sse_data_lines)
            if event:
                yield event

    # ------------------------------------------------------------------
    # SSE / JSON parsing helpers
    # ------------------------------------------------------------------

    def _parse_sse_event(self, event_name: str | None, data_lines: Iterable[str]) -> Dict[str, Any] | None:
        data = "\n".join(data_lines).strip()
        if not data or data == "[DONE]":
            return {"type": "done"} if data == "[DONE]" else None
        return self._parse_json_event(data, default_type=event_name or "message")

    def _parse_json_event(self, payload: str, default_type: str = "message") -> Dict[str, Any] | None:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.error("[AGENTCORE] JSON parse error: %s — payload: %.100s", exc, payload)
            return {"type": "error", "message": f"Parse error: {exc}", "recoverable": True}

        if not isinstance(event, dict):
            return {"type": "error", "message": "Expected JSON object", "recoverable": True}

        if "type" not in event:
            # BedrockAgentCoreApp native: {"response": "...", "status": "success|error"}
            if "response" in event:
                if event.get("status") == "error":
                    return {"type": "error", "message": str(event["response"])}
                response_text = str(event["response"])
                if response_text.strip().startswith("{"):
                    nested_event = self._parse_json_event(response_text, default_type=default_type)
                    if nested_event:
                        return nested_event
                if getattr(settings, "agent_core_require_true_streaming", True):
                    return {
                        "type": "error",
                        "error_code": "TRUE_STREAMING_REQUIRED",
                        "message": (
                            "Agent Core returned native response text without an explicit "
                            "token event. Synthetic streaming is disabled."
                        ),
                        "recoverable": False,
                    }
                return {"type": "token", "content": response_text}
            event["type"] = default_type

        return event

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()
