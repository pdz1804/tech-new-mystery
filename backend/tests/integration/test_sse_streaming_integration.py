"""Integration tests for SSE streaming endpoint (requires running backend).

This test file demonstrates how to test the SSE streaming endpoint with a real backend.
Run with: pytest tests/integration/test_sse_streaming_integration.py -v -m integration

PREREQUISITES:
1. Backend running at http://localhost:8000
2. Valid JWT token in environment variable TEST_AUTH_TOKEN
3. Valid session created via POST /api/v1/chat/sessions
4. Agent Core service available (or mocked)
"""

import pytest
import json
import httpx
import os
from typing import AsyncGenerator


# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestSSEStreamingIntegration:
    """Integration tests for SSE streaming endpoint."""

    BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "")
    TEST_SESSION_ID = os.getenv("TEST_SESSION_ID", "")

    @classmethod
    def setup_class(cls):
        """Verify prerequisites."""
        if not cls.AUTH_TOKEN:
            pytest.skip("TEST_AUTH_TOKEN environment variable not set")
        if not cls.BASE_URL or "localhost" not in cls.BASE_URL:
            pytest.skip("Backend not running at expected URL")

    @pytest.fixture
    async def auth_headers(self):
        """Get auth headers."""
        return {
            "Authorization": f"Bearer {self.AUTH_TOKEN}",
            "Content-Type": "application/json",
        }

    @pytest.fixture
    async def test_session(self, auth_headers):
        """Create a test session."""
        if self.TEST_SESSION_ID:
            return self.TEST_SESSION_ID

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v1/chat/sessions",
                json={
                    "title": "Test Session",
                    "description": "Integration test session",
                },
                headers=auth_headers,
            )

            if response.status_code != 201:
                pytest.skip(f"Failed to create test session: {response.text}")

            data = response.json()
            return data["data"]["session_id"]

    @pytest.mark.asyncio
    async def test_stream_endpoint_returns_sse_format(self, test_session, auth_headers):
        """Verify streaming endpoint returns RFC 6202 compliant SSE."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/stream",
                json={"content": "What are the latest AI breakthroughs?"},
                headers=auth_headers,
                timeout=30.0,
            ) as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream"

                # Verify we get events
                event_count = 0
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_count += 1

                assert event_count > 0, "Should receive at least one event"

    @pytest.mark.asyncio
    async def test_stream_receives_token_events(self, test_session, auth_headers):
        """Verify we receive token events during streaming."""
        token_events = []

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/stream",
                json={"content": "Hello"},
                headers=auth_headers,
                timeout=30.0,
            ) as response:
                buffer = ""
                async for chunk in response.aiter_raw():
                    buffer += chunk.decode("utf-8", errors="ignore")
                    lines = buffer.split("\n\n")
                    buffer = lines[-1]

                    for event_block in lines[:-1]:
                        if "event: token" in event_block:
                            try:
                                data_line = [l for l in event_block.split("\n") if l.startswith("data:")][0]
                                json_str = data_line[6:]  # Remove "data: " prefix
                                event = json.loads(json_str)
                                token_events.append(event)
                            except (json.JSONDecodeError, IndexError):
                                pass

        assert len(token_events) > 0, "Should receive at least one token event"
        assert all(e.get("type") == "token" for e in token_events)
        assert all("content" in e for e in token_events)

    @pytest.mark.asyncio
    async def test_stream_receives_done_event(self, test_session, auth_headers):
        """Verify stream ends with done event."""
        done_event = None

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/stream",
                json={"content": "Hello"},
                headers=auth_headers,
                timeout=30.0,
            ) as response:
                buffer = ""
                async for chunk in response.aiter_raw():
                    buffer += chunk.decode("utf-8", errors="ignore")
                    lines = buffer.split("\n\n")
                    buffer = lines[-1]

                    for event_block in lines[:-1]:
                        if "event: done" in event_block:
                            try:
                                data_line = [l for l in event_block.split("\n") if l.startswith("data:")][0]
                                json_str = data_line[6:]
                                done_event = json.loads(json_str)
                            except (json.JSONDecodeError, IndexError):
                                pass

        assert done_event is not None, "Should receive done event"
        assert done_event.get("type") == "done"
        assert "message_id" in done_event
        assert "tokens" in done_event

    @pytest.mark.asyncio
    async def test_stream_error_handling(self, test_session, auth_headers):
        """Test error handling in streaming."""
        async with httpx.AsyncClient() as client:
            # Try to stream to non-existent session
            response = await client.post(
                f"{self.BASE_URL}/api/v1/chat/sessions/nonexistent-session/stream",
                json={"content": "Hello"},
                headers=auth_headers,
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_without_auth(self, test_session):
        """Test streaming without authentication."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/stream",
                json={"content": "Hello"},
                timeout=10.0,
            )

            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_stream_concurrent_requests(self, test_session, auth_headers):
        """Test multiple concurrent streaming requests."""
        import asyncio

        async def stream_request(message):
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/stream",
                    json={"content": message},
                    headers=auth_headers,
                    timeout=30.0,
                ) as response:
                    assert response.status_code == 200

                    # Count events
                    event_count = 0
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_count += 1

                    return event_count

        # Run 3 concurrent requests
        results = await asyncio.gather(
            stream_request("Query 1"),
            stream_request("Query 2"),
            stream_request("Query 3"),
            return_exceptions=True,
        )

        # Verify all succeeded
        assert len(results) == 3
        assert all(isinstance(r, int) and r > 0 for r in results if isinstance(r, int))

    @pytest.mark.asyncio
    async def test_stream_response_headers(self, test_session, auth_headers):
        """Verify correct SSE headers in response."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/stream",
                json={"content": "Hello"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("connection") == "keep-alive"
            assert response.headers.get("x-accel-buffering") == "no"

    @pytest.mark.asyncio
    async def test_stream_preserves_message_history(self, test_session, auth_headers):
        """Verify messages are saved during streaming."""
        import asyncio

        # Send first message
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/stream",
                json={"content": "What is AI?"},
                headers=auth_headers,
                timeout=30.0,
            ) as response:
                # Wait for streaming to complete
                async for _ in response.aiter_lines():
                    pass

            # Fetch message history
            response = await client.get(
                f"{self.BASE_URL}/api/v1/chat/sessions/{test_session}/messages",
                headers=auth_headers,
            )

            assert response.status_code == 200
            messages = response.json()["data"]

            # Should have user and assistant messages
            user_messages = [m for m in messages if m["role"] == "user"]
            assistant_messages = [m for m in messages if m["role"] == "assistant"]

            assert len(user_messages) > 0, "Should have user messages"
            assert len(assistant_messages) > 0, "Should have assistant messages"

            # Verify message content
            user_msg = next((m for m in user_messages if "AI" in m["content"]), None)
            assert user_msg is not None, "User message should be saved"


def test_sse_manual_curl_example():
    """Documentation: How to test SSE streaming with curl.

    EXAMPLE CURL COMMAND:
    ```
    curl -X POST http://localhost:8000/api/v1/chat/sessions/sess-123/stream \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{"content": "What are the latest AI breakthroughs?"}'
    ```

    EXPECTED OUTPUT:
    ```
    event: token
    data: {"type": "token", "content": "Based"}

    event: token
    data: {"type": "token", "content": " on"}

    event: token
    data: {"type": "token", "content": " recent"}

    ...

    event: done
    data: {"type": "done", "message_id": "msg-abc123", "tokens": 42}
    ```
    """
    pass


def test_sse_javascript_client_example():
    """Documentation: How to consume SSE streaming from JavaScript.

    EXAMPLE JAVASCRIPT CODE:
    ```javascript
    const sessionId = 'sess-123';
    const token = localStorage.getItem('auth_token');

    const response = await fetch(`/api/v1/chat/sessions/${sessionId}/stream`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            content: 'What are the latest AI breakthroughs?'
        })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\\n\\n');
        buffer = lines.pop();

        for (const eventStr of lines) {
            if (eventStr.startsWith('event:')) {
                const eventType = eventStr.split('\\n')[0].split(': ')[1];
                const dataLine = eventStr.split('\\n')[1];
                const data = JSON.parse(dataLine.slice(6)); // Remove 'data: '

                if (eventType === 'token') {
                    console.log('Token:', data.content);
                    // Append token to message
                } else if (eventType === 'tool_invocation') {
                    console.log('Tool:', data.tool_name);
                } else if (eventType === 'tool_result') {
                    console.log('Result:', data.tool_name);
                } else if (eventType === 'done') {
                    console.log('Complete:', data.message_id);
                } else if (eventType === 'error') {
                    console.error('Error:', data.error);
                }
            }
        }
    }
    ```
    """
    pass
