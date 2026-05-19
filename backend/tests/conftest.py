"""Pytest configuration and fixtures."""

import os
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

# Clear LocalStack endpoint for tests
if "DYNAMODB_ENDPOINT_URL" in os.environ:
    del os.environ["DYNAMODB_ENDPOINT_URL"]

from app.main import app


@pytest.fixture
def mock_ddb():
    """Mock DynamoDB for testing."""
    with mock_aws():
        yield


@pytest.fixture
def client(mock_ddb):
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Authentication headers for protected endpoints."""
    return {"Authorization": "Bearer fake-token"}
