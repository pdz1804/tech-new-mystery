"""Pytest configuration and fixtures for E2E tests."""

import asyncio
import os
import logging
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Test configuration from environment or defaults
BACKEND_URL = os.getenv("TEST_BACKEND_URL", "http://localhost:8000")
BACKEND_TIMEOUT = float(os.getenv("TEST_BACKEND_TIMEOUT", "60"))
TEST_USER_ID = os.getenv("TEST_USER_ID", "test-e2e-user")
TEST_AUTH_TOKEN = os.getenv("TEST_AUTH_TOKEN", "Bearer test-token-e2e")


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP client for backend calls with proper cleanup."""
    async with httpx.AsyncClient(
        base_url=BACKEND_URL,
        timeout=httpx.Timeout(BACKEND_TIMEOUT),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    ) as client:
        logger.info(f"HTTP client created for {BACKEND_URL}")
        yield client
        logger.info("HTTP client closed")


@pytest_asyncio.fixture
async def auth_token() -> str:
    """Provide authentication token for test requests."""
    logger.debug(f"Using auth token: {TEST_AUTH_TOKEN[:20]}...")
    return TEST_AUTH_TOKEN


@pytest_asyncio.fixture
async def test_user_id() -> str:
    """Provide test user ID."""
    return TEST_USER_ID


@pytest_asyncio.fixture
async def cleanup_sessions(http_client: httpx.AsyncClient, auth_token: str):
    """Fixture to cleanup test sessions after tests complete.

    Collects session IDs created during tests and archives them.
    """
    created_sessions = []
    created_messages = []

    yield created_sessions, created_messages

    # Cleanup Phase
    logger.info(f"Cleaning up {len(created_sessions)} sessions...")

    for session_id in created_sessions:
        try:
            # Get session to verify it exists
            response = await http_client.get(
                f"/api/v1/chat/sessions/{session_id}",
                headers={"Authorization": auth_token},
            )
            if response.status_code == 200:
                logger.debug(f"Session {session_id} exists, cleaning up")
                # In future: implement archive endpoint
                # For now, just verify it exists
        except Exception as e:
            logger.warning(f"Error verifying session {session_id}: {e}")

    logger.info(f"Cleanup complete for {len(created_sessions)} sessions")


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line(
        "markers",
        "performance: marks tests as performance tests",
    )

    logger.info(f"Running E2E tests against {BACKEND_URL}")
    logger.info(f"Test timeout: {BACKEND_TIMEOUT}s")


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    for item in items:
        # Add asyncio marker to all async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def backend_ready(http_client: httpx.AsyncClient):
    """Verify backend is ready before running tests."""
    max_retries = 5
    retry_delay = 0.5

    for attempt in range(max_retries):
        try:
            response = await http_client.get("/health", timeout=5.0)
            if response.status_code == 200:
                logger.info("Backend is ready")
                return True
        except Exception as e:
            logger.debug(f"Health check attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

    logger.error(f"Backend not ready after {max_retries} retries")
    pytest.skip(f"Backend not ready at {BACKEND_URL}")


# ============================================================================
# HOOKS
# ============================================================================


def pytest_runtest_setup(item):
    """Setup for each test."""
    logger.debug(f"Setting up test: {item.name}")


def pytest_runtest_teardown(item, nextitem):
    """Teardown for each test."""
    logger.debug(f"Tearing down test: {item.name}")


@pytest.hookimpl(tryfirst=True)
def pytest_exception_interact(node, call, report):
    """Log exceptions that occur during tests."""
    if report.failed:
        logger.error(f"Test failed: {node.name}")
        if call.excinfo:
            logger.error(f"Exception: {call.excinfo.value}")
