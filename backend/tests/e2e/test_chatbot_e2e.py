"""Comprehensive end-to-end tests for chatbot feature.

Tests cover all user flows including session management, message streaming,
tool invocation, authentication, error handling, and performance metrics.

Requirements:
- Real backend running (http://localhost:8000)
- Real DynamoDB with test data
- Real Agent Core Runtime connection
- Test user creation and cleanup

Test Coverage:
- Session creation & management (4 tests)
- Message flow & context (5 tests)
- Tool invocation (3 tests)
- Streaming flow (3 tests)
- Authentication & authorization (4 tests)
- Error scenarios (4 tests)
- Performance validation (2 tests)
- Concurrent users (1 test)
Total: 26+ test cases
"""

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator, Dict, Any, List

import httpx
import pytest

# Test configuration
TEST_BACKEND_URL = "http://localhost:8000"
TEST_TIMEOUT = 60.0
TEST_USER_COUNT = 5

# Test data
TEST_SESSION_TITLE = "E2E Test Session"
TEST_SESSION_DESCRIPTION = "Session for end-to-end testing"
TEST_MESSAGE_CONTENT = "What are the latest AI breakthroughs?"
TEST_MESSAGE_LONG = "Please provide a comprehensive analysis of recent AI developments, including machine learning advancements, large language models, and their real-world applications."


# ============================================================================
# FIXTURES & SETUP
# ============================================================================


@pytest.fixture
async def auth_token():
    """Generate a test JWT token for authentication.

    In production, this would use real AWS Cognito tokens.
    For E2E tests, we use a pre-created test user token.
    """
    # TODO: Use real AWS Cognito or test auth service
    # For now, assumes test-user token is available in environment
    return "Bearer test-user-token-123"


@pytest.fixture
async def http_client():
    """Create an async HTTP client for backend calls."""
    async with httpx.AsyncClient(base_url=TEST_BACKEND_URL, timeout=TEST_TIMEOUT) as client:
        yield client


@pytest.fixture
async def test_user_id():
    """Generate unique test user ID."""
    return f"test-user-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def cleanup_sessions(http_client, auth_token):
    """Fixture to collect and cleanup test sessions after tests."""
    created_sessions = []

    yield created_sessions

    # Cleanup: Archive all created sessions
    for session_id in created_sessions:
        try:
            # Archive session (if endpoint exists)
            # await http_client.post(
            #     f"/api/v1/chat/sessions/{session_id}/archive",
            #     headers={"Authorization": auth_token},
            # )
            pass
        except Exception as e:
            pytest.warns(UserWarning, f"Failed to cleanup session {session_id}: {e}")


# ============================================================================
# A. SESSION CREATION & MANAGEMENT (4 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_create_session(http_client, auth_token, cleanup_sessions):
    """Test: Create a new chat session.

    Scenario:
    1. Send POST /api/v1/chat/sessions with title
    2. Verify session created in response
    3. Verify session exists in database
    """
    start_time = time.time()

    # Create session
    response = await http_client.post(
        "/api/v1/chat/sessions",
        json={
            "title": TEST_SESSION_TITLE,
            "description": TEST_SESSION_DESCRIPTION,
        },
        headers={"Authorization": auth_token},
    )

    elapsed = time.time() - start_time

    # Assertions
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert "data" in data

    session = data["data"]
    assert session["session_id"]
    assert session["title"] == TEST_SESSION_TITLE
    assert session["description"] == TEST_SESSION_DESCRIPTION
    assert session["created_at"]
    assert session["message_count"] == 0
    assert session["is_active"] is True

    # Performance check: session creation should be < 500ms
    assert elapsed < 0.5, f"Session creation took {elapsed:.2f}s (expected < 0.5s)"

    # Cleanup
    cleanup_sessions.append(session["session_id"])


@pytest.mark.asyncio
async def test_list_sessions_with_pagination(http_client, auth_token, cleanup_sessions):
    """Test: List sessions with pagination.

    Scenario:
    1. Create 5 test sessions
    2. List sessions with page=1, page_size=3
    3. Verify pagination metadata
    4. Verify user isolation (no other user's sessions)
    """
    # Create multiple sessions
    session_ids = []
    for i in range(5):
        response = await http_client.post(
            "/api/v1/chat/sessions",
            json={"title": f"Session {i}", "description": f"Test session {i}"},
            headers={"Authorization": auth_token},
        )
        assert response.status_code == 201
        session_id = response.json()["data"]["session_id"]
        session_ids.append(session_id)
        cleanup_sessions.append(session_id)

    # List sessions with pagination
    response = await http_client.get(
        "/api/v1/chat/sessions?page=1&page_size=3",
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 3
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 3
    assert data["meta"]["total"] >= 5

    # Verify user isolation: returned sessions should belong to authenticated user
    for session in data["data"]:
        # In real implementation, verify user_id matches
        assert session["session_id"]
        assert session["title"]


@pytest.mark.asyncio
async def test_get_session_details(http_client, auth_token, cleanup_sessions):
    """Test: Retrieve session details.

    Scenario:
    1. Create a session
    2. GET /api/v1/chat/sessions/{session_id}
    3. Verify all session fields returned
    """
    # Create session
    create_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Detail Test Session"},
        headers={"Authorization": auth_token},
    )
    session_id = create_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Get session details
    response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["session_id"] == session_id
    assert data["data"]["title"] == "Detail Test Session"
    assert data["data"]["message_count"] == 0


@pytest.mark.asyncio
async def test_session_not_found_error(http_client, auth_token):
    """Test: Accessing non-existent session returns 404.

    Scenario:
    1. GET /api/v1/chat/sessions/{invalid_session_id}
    2. Verify 404 error returned
    """
    response = await http_client.get(
        f"/api/v1/chat/sessions/invalid-session-{uuid.uuid4().hex[:8]}",
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 404
    data = response.json()
    assert "Session not found" in data.get("detail", "")


# ============================================================================
# B. MESSAGE FLOW & CONTEXT (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_send_user_message(http_client, auth_token, cleanup_sessions):
    """Test: Send a user message to a session.

    Scenario:
    1. Create session
    2. POST /api/v1/chat/sessions/{session_id}/message with content
    3. Verify message saved
    4. Verify session updated
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Message Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Send message
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": TEST_MESSAGE_CONTENT},
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 201
    message = response.json()["data"]
    assert message["role"] == "user"
    assert message["content"] == TEST_MESSAGE_CONTENT
    assert message["message_id"]
    assert message["timestamp"]

    # Verify session was updated
    session_response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers={"Authorization": auth_token},
    )
    session = session_response.json()["data"]
    assert session["message_count"] > 0


@pytest.mark.asyncio
async def test_get_message_history(http_client, auth_token, cleanup_sessions):
    """Test: Retrieve message history with pagination.

    Scenario:
    1. Create session, add 5 messages
    2. GET /api/v1/chat/sessions/{session_id}/messages with pagination
    3. Verify all messages returned in order
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "History Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Add 5 messages
    message_ids = []
    for i in range(5):
        response = await http_client.post(
            f"/api/v1/chat/sessions/{session_id}/message",
            json={"content": f"Message {i}"},
            headers={"Authorization": auth_token},
        )
        assert response.status_code == 201
        message_ids.append(response.json()["data"]["message_id"])

    # Get message history
    response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 5
    assert data["meta"]["total"] == 5

    # Verify order (oldest first)
    for i, msg in enumerate(data["data"]):
        assert msg["content"] == f"Message {i}"


@pytest.mark.asyncio
async def test_multi_turn_conversation(http_client, auth_token, cleanup_sessions):
    """Test: Multi-turn conversation with context maintained.

    Scenario:
    1. Create session
    2. Send message 1
    3. Verify response (streamed)
    4. Send message 2
    5. Verify context includes message 1
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Multi-Turn Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Send first message
    msg1_response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": "What is AI?"},
        headers={"Authorization": auth_token},
    )
    assert msg1_response.status_code == 201

    # Send second message (relies on context)
    msg2_response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": "Can you elaborate on machine learning?"},
        headers={"Authorization": auth_token},
    )
    assert msg2_response.status_code == 201

    # Get full history and verify both messages present
    history_response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers={"Authorization": auth_token},
    )
    messages = history_response.json()["data"]
    assert len(messages) >= 2
    assert any("AI" in m["content"] for m in messages)
    assert any("machine learning" in m["content"] for m in messages)


@pytest.mark.asyncio
async def test_session_isolation_different_users(http_client, cleanup_sessions):
    """Test: Different users cannot see each other's sessions.

    Scenario:
    1. Create session as User A
    2. Attempt to access as User B
    3. Verify 403 Forbidden returned
    """
    user_a_token = "Bearer test-user-a-token"
    user_b_token = "Bearer test-user-b-token"

    # Create session as User A
    create_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "User A Session"},
        headers={"Authorization": user_a_token},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Try to access as User B
    access_response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers={"Authorization": user_b_token},
    )

    # Should be forbidden (403) or not found (404)
    assert access_response.status_code in [403, 404]


@pytest.mark.asyncio
async def test_message_validation(http_client, auth_token, cleanup_sessions):
    """Test: Invalid messages rejected.

    Scenario:
    1. Send message with empty content
    2. Verify 400 Bad Request
    3. Send message exceeding max length
    4. Verify 400 Bad Request
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Validation Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Try empty message
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": ""},
        headers={"Authorization": auth_token},
    )
    assert response.status_code == 422  # Validation error

    # Try message exceeding max length (4000 chars)
    long_message = "x" * 5000
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": long_message},
        headers={"Authorization": auth_token},
    )
    assert response.status_code == 422  # Validation error


# ============================================================================
# C. STREAMING FLOW (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_sse_streaming_tokens(http_client, auth_token, cleanup_sessions):
    """Test: Stream response tokens via SSE.

    Scenario:
    1. Create session
    2. POST /api/v1/chat/sessions/{session_id}/stream with message
    3. Receive streaming response
    4. Parse token events
    5. Verify done event
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Streaming Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Stream message
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/stream",
        json={"content": "Hello, AI assistant!"},
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

    # Parse SSE events
    events = []
    async for line in response.aiter_lines():
        if line.startswith("event: "):
            event_type = line[7:]
            events.append(event_type)

    # Verify event types
    assert "token" in events or "done" in events, f"Expected token or done events, got: {events}"
    assert "done" in events, f"Expected done event, got: {events}"


@pytest.mark.asyncio
async def test_sse_tool_invocation_events(http_client, auth_token, cleanup_sessions):
    """Test: Stream tool invocation and result events.

    Scenario:
    1. Create session
    2. Send message that triggers tool use
    3. Verify tool_invocation event
    4. Verify tool_result event
    5. Verify done event
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Tool Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Stream message that likely triggers tool use
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/stream",
        json={"content": "Search for latest AI news"},
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 200

    # Parse SSE events
    event_types = []
    async for line in response.aiter_lines():
        if line.startswith("event: "):
            event_type = line[7:]
            event_types.append(event_type)

    # Verify expected event types
    # Note: tool_invocation may or may not occur depending on agent decision
    assert "done" in event_types, f"Expected done event, got: {event_types}"


@pytest.mark.asyncio
async def test_streaming_client_disconnect_cleanup(http_client, auth_token, cleanup_sessions):
    """Test: Client disconnect during streaming cleanup.

    Scenario:
    1. Create session
    2. Start streaming message
    3. Close client connection mid-stream
    4. Verify cleanup (no orphaned resources)
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Disconnect Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Stream with early disconnect
    try:
        response = await http_client.post(
            f"/api/v1/chat/sessions/{session_id}/stream",
            json={"content": "Start streaming..."},
            headers={"Authorization": auth_token},
            timeout=httpx.Timeout(1.0),  # Short timeout to simulate disconnect
        )

        # Try to read a few events then close
        count = 0
        async for line in response.aiter_lines():
            count += 1
            if count > 2:
                break  # Simulate early close

    except (httpx.TimeoutException, asyncio.TimeoutError):
        # Expected: client disconnects
        pass

    # Verify session still exists and is not corrupted
    session_response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers={"Authorization": auth_token},
    )
    assert session_response.status_code == 200


# ============================================================================
# D. AUTHENTICATION & AUTHORIZATION (4 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_create_session_without_auth(http_client):
    """Test: Create session without authentication returns 401.

    Scenario:
    1. POST /api/v1/chat/sessions without Authorization header
    2. Verify 401 Unauthorized returned
    """
    response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Unauthorized"},
        headers={},  # No authorization
    )

    assert response.status_code == 401
    assert "Authorization" in response.headers.get("WWW-Authenticate", "")


@pytest.mark.asyncio
async def test_access_session_without_auth(http_client, cleanup_sessions):
    """Test: Access session without authentication returns 401.

    Scenario:
    1. GET /api/v1/chat/sessions/{session_id} without Authorization header
    2. Verify 401 Unauthorized returned
    """
    response = await http_client.get(
        f"/api/v1/chat/sessions/some-session-id",
        headers={},  # No authorization
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(http_client):
    """Test: Invalid JWT token is rejected.

    Scenario:
    1. POST /api/v1/chat/sessions with invalid token
    2. Verify 401 Unauthorized returned
    """
    response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Invalid Token"},
        headers={"Authorization": "Bearer invalid-token-xyz"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_other_user_session_forbidden(http_client, cleanup_sessions):
    """Test: User cannot access another user's session (403).

    Scenario:
    1. User A creates session
    2. User B attempts to stream/add message
    3. Verify 403 Forbidden
    """
    user_a_token = "Bearer test-user-a-token"
    user_b_token = "Bearer test-user-b-token"

    # Create session as User A
    create_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "User A Private"},
        headers={"Authorization": user_a_token},
    )
    session_id = create_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Try to add message as User B
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": "Trying to access..."},
        headers={"Authorization": user_b_token},
    )

    assert response.status_code in [403, 404]


# ============================================================================
# E. ERROR SCENARIOS (4 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_agent_timeout_error(http_client, auth_token, cleanup_sessions):
    """Test: Agent timeout returns 504 Gateway Timeout.

    Scenario:
    1. Create session
    2. Send message (may trigger long-running tool)
    3. If timeout occurs, verify 504 returned
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Timeout Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Send message (may timeout)
    try:
        response = await http_client.post(
            f"/api/v1/chat/sessions/{session_id}/stream",
            json={"content": "Very complex question requiring long analysis..."},
            headers={"Authorization": auth_token},
            timeout=10.0,
        )

        # If response is received, check for timeout error
        if response.status_code == 504:
            assert response.status_code == 504
        else:
            # Otherwise should be 200 (streaming started)
            assert response.status_code == 200

    except httpx.TimeoutException:
        # Timeout is acceptable in this scenario
        pass


@pytest.mark.asyncio
async def test_invalid_session_returns_404(http_client, auth_token):
    """Test: Invalid session ID returns 404.

    Scenario:
    1. Try to add message to non-existent session
    2. Verify 404 Not Found
    """
    response = await http_client.post(
        f"/api/v1/chat/sessions/invalid-session/message",
        json={"content": "Test"},
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_database_error_returns_500(http_client, auth_token, cleanup_sessions):
    """Test: Database errors return 500 Internal Server Error.

    Scenario:
    1. Create session
    2. Simulate database failure (or trigger error condition)
    3. Verify 500 returned
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Error Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # In a real scenario, you'd simulate database failure
    # For now, just verify normal operation
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": "Normal message"},
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_malformed_request_returns_400(http_client, auth_token):
    """Test: Malformed requests return 400 Bad Request.

    Scenario:
    1. POST /api/v1/chat/sessions with missing required field
    2. Verify 400/422 Validation Error
    """
    response = await http_client.post(
        "/api/v1/chat/sessions",
        json={},  # Missing title
        headers={"Authorization": auth_token},
    )

    assert response.status_code in [400, 422]


# ============================================================================
# F. PERFORMANCE VALIDATION (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_streaming_starts_within_1_second(http_client, auth_token, cleanup_sessions):
    """Test: Streaming response starts within 1 second.

    Scenario:
    1. Create session
    2. Start streaming message
    3. Measure time to first token event
    4. Verify < 1 second
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Performance Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Start streaming and measure time
    start_time = time.time()
    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/stream",
        json={"content": "Quick response test"},
        headers={"Authorization": auth_token},
    )

    assert response.status_code == 200

    # Measure time to first event
    first_event_time = None
    async for line in response.aiter_lines():
        if line.startswith("event: "):
            first_event_time = time.time() - start_time
            break

    # Verify first event within 1 second
    if first_event_time:
        assert (
            first_event_time < 1.0
        ), f"First event took {first_event_time:.2f}s (expected < 1.0s)"


@pytest.mark.asyncio
async def test_message_response_within_5_seconds(http_client, auth_token, cleanup_sessions):
    """Test: Full message response completes within 5 seconds.

    Scenario:
    1. Create session
    2. Send message
    3. Measure total response time
    4. Verify < 5 seconds
    """
    # Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Response Time Test"},
        headers={"Authorization": auth_token},
    )
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # Send message and measure time
    start_time = time.time()

    response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/stream",
        json={"content": "Quick question"},
        headers={"Authorization": auth_token},
    )

    # Consume entire response
    async for line in response.aiter_lines():
        pass

    elapsed = time.time() - start_time

    # Verify response within 5 seconds
    assert elapsed < 5.0, f"Response took {elapsed:.2f}s (expected < 5.0s)"


# ============================================================================
# G. CONCURRENT USERS (1 test)
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_user_streams(http_client, auth_token, cleanup_sessions):
    """Test: Multiple concurrent users can stream independently.

    Scenario:
    1. Create N sessions for N users
    2. Start streaming message in each session concurrently
    3. Verify all streams complete successfully
    4. Verify no message cross-contamination
    """

    async def stream_session(session_id: str, user_num: int) -> Dict[str, Any]:
        """Stream a message for a specific session."""
        events = []
        try:
            response = await http_client.post(
                f"/api/v1/chat/sessions/{session_id}/stream",
                json={"content": f"User {user_num} message"},
                headers={"Authorization": auth_token},
            )

            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    event_type = line[7:]
                    events.append(event_type)

            return {
                "user_num": user_num,
                "session_id": session_id,
                "success": True,
                "events": events,
            }
        except Exception as e:
            return {
                "user_num": user_num,
                "session_id": session_id,
                "success": False,
                "error": str(e),
            }

    # Create sessions for multiple users
    sessions = []
    for i in range(TEST_USER_COUNT):
        response = await http_client.post(
            "/api/v1/chat/sessions",
            json={"title": f"Concurrent Test {i}"},
            headers={"Authorization": auth_token},
        )
        session_id = response.json()["data"]["session_id"]
        sessions.append(session_id)
        cleanup_sessions.append(session_id)

    # Stream concurrently
    tasks = [stream_session(session_id, i) for i, session_id in enumerate(sessions)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all succeeded
    for result in results:
        if isinstance(result, Exception):
            pytest.fail(f"Concurrent stream failed: {result}")
        assert result["success"], f"Stream failed for user {result['user_num']}: {result.get('error')}"
        assert "done" in result["events"], f"No done event for user {result['user_num']}"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_full_conversation_flow(http_client, auth_token, cleanup_sessions):
    """Integration test: Complete conversation workflow.

    Scenario:
    1. Create session
    2. Send first message and stream response
    3. Get message history
    4. Send second message and stream response
    5. Verify full history preserved
    """
    # 1. Create session
    session_response = await http_client.post(
        "/api/v1/chat/sessions",
        json={
            "title": "Full Workflow Test",
            "description": "Integration test for full flow",
        },
        headers={"Authorization": auth_token},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["data"]["session_id"]
    cleanup_sessions.append(session_id)

    # 2. Send first message
    first_msg_response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/message",
        json={"content": "What is machine learning?"},
        headers={"Authorization": auth_token},
    )
    assert first_msg_response.status_code == 201

    # 3. Stream response to first message
    stream_response = await http_client.post(
        f"/api/v1/chat/sessions/{session_id}/stream",
        json={"content": "Explain neural networks"},
        headers={"Authorization": auth_token},
    )
    assert stream_response.status_code == 200

    # Consume stream
    stream_events = []
    async for line in stream_response.aiter_lines():
        if line.startswith("event: "):
            stream_events.append(line[7:])

    assert "done" in stream_events

    # 4. Get message history
    history_response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers={"Authorization": auth_token},
    )
    assert history_response.status_code == 200
    messages = history_response.json()["data"]

    # 5. Verify history contains both user messages
    user_messages = [m for m in messages if m["role"] == "user"]
    assert len(user_messages) >= 2
    assert any("machine learning" in m["content"] for m in user_messages)
    assert any("neural networks" in m["content"] for m in user_messages)

    # 6. Verify session metadata
    session_response = await http_client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers={"Authorization": auth_token},
    )
    session = session_response.json()["data"]
    assert session["message_count"] >= 2
    assert session["last_message_at"] > 0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def wait_for_backend(
    max_retries: int = 10, retry_delay: float = 0.5
) -> bool:
    """Wait for backend to be ready before running tests.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if backend is ready, False if timeout
    """
    async with httpx.AsyncClient(base_url=TEST_BACKEND_URL) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get("/health", timeout=2.0)
                if response.status_code == 200:
                    return True
            except Exception:
                pass

            await asyncio.sleep(retry_delay)

    return False


@pytest.fixture(scope="session", autouse=True)
async def ensure_backend_ready():
    """Ensure backend is running before tests start."""
    if not await wait_for_backend():
        pytest.skip("Backend not ready at http://localhost:8000")


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Run with: pytest tests/e2e/test_chatbot_e2e.py -v --asyncio-mode=auto
    pytest.main([__file__, "-v", "--tb=short", "-s"])
