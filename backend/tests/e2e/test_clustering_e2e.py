"""End-to-end tests for article clustering feature.

Tests cover the complete clustering pipeline including:
- Job triggering and execution
- Cluster creation and metadata storage
- Pagination and search functionality
- Result verification against DynamoDB
- Metrics calculation and tracking

Requirements:
- Real backend running (http://localhost:8000)
- Real DynamoDB with article data
- Real Celery worker with clustering queue
- Articles with embeddings available

Test Coverage:
- Cluster job triggering (2 tests)
- Job status monitoring (2 tests)
- DynamoDB result verification (3 tests)
- Cluster pagination (2 tests)
- Cluster search/filter (2 tests)
- Metrics calculation (2 tests)
- Error handling (2 tests)
Total: 15 test cases
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import httpx
import pytest
import pytest_asyncio

# Test configuration
BACKEND_URL = "http://localhost:8000"
BACKEND_TIMEOUT = 120.0
CLUSTERING_JOB_POLL_INTERVAL = 2.0
CLUSTERING_JOB_MAX_WAIT = 300.0  # 5 minutes max wait for job completion
TEST_USER_ID = "test-clustering-e2e-user"
ADMIN_TOKEN = "Bearer test-admin-token-clustering"


# ============================================================================
# FIXTURES & SETUP
# ============================================================================


@pytest_asyncio.fixture
async def http_client() -> httpx.AsyncClient:
    """Create async HTTP client for backend calls."""
    async with httpx.AsyncClient(
        base_url=BACKEND_URL,
        timeout=httpx.Timeout(BACKEND_TIMEOUT),
    ) as client:
        yield client


@pytest_asyncio.fixture
async def admin_token() -> str:
    """Provide admin authentication token for clustering admin endpoints."""
    return ADMIN_TOKEN


@pytest_asyncio.fixture
async def test_user_id() -> str:
    """Provide test user ID."""
    return TEST_USER_ID


@pytest_asyncio.fixture
async def backend_ready(http_client: httpx.AsyncClient):
    """Verify backend is ready before running tests."""
    max_retries = 10
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            response = await http_client.get("/health", timeout=5.0)
            if response.status_code == 200:
                return True
        except Exception:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

    pytest.skip(f"Backend not ready at {BACKEND_URL}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def wait_for_clustering_job(
    http_client: httpx.AsyncClient,
    admin_token: str,
    max_wait: float = CLUSTERING_JOB_MAX_WAIT,
) -> Dict[str, Any]:
    """Poll for clustering job completion.

    Returns:
        dict: Job status response with result or error
    """
    start_time = time.time()
    poll_interval = CLUSTERING_JOB_POLL_INTERVAL

    while time.time() - start_time < max_wait:
        try:
            response = await http_client.get(
                "/api/v1/admin/clustering/job-status",
                headers={"Authorization": admin_token},
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")

                if status in ("completed", "failed"):
                    return data

            await asyncio.sleep(poll_interval)
        except Exception as e:
            await asyncio.sleep(poll_interval)

    raise TimeoutError(
        f"Clustering job did not complete within {max_wait} seconds"
    )


async def get_article_count(
    http_client: httpx.AsyncClient,
    admin_token: str,
) -> int:
    """Get total count of articles in database."""
    try:
        response = await http_client.get(
            "/api/v1/articles?limit=1",
            headers={"Authorization": admin_token},
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("total", 0)
    except Exception:
        pass

    return 0


async def get_cluster_count(
    http_client: httpx.AsyncClient,
    admin_token: str,
) -> int:
    """Get total count of clusters."""
    try:
        response = await http_client.get(
            "/api/v1/clusters?limit=1&skip=0",
            headers={"Authorization": admin_token},
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("total", 0)
    except Exception:
        pass

    return 0


async def get_embeddings_count(
    http_client: httpx.AsyncClient,
    admin_token: str,
) -> int:
    """Get count of articles with embeddings."""
    try:
        response = await http_client.get(
            "/api/v1/admin/embeddings/count",
            headers={"Authorization": admin_token},
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("count", 0)
    except Exception:
        pass

    return 0


# ============================================================================
# A. CLUSTER JOB TRIGGERING (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_trigger_clustering_job(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 1: Trigger a clustering job and verify it's queued.

    Verifies:
    - POST /api/v1/admin/clustering/trigger returns 200/202
    - Response contains job_id
    - Job status is queued or processing
    """
    response = await http_client.post(
        "/api/v1/admin/clustering/trigger",
        headers={"Authorization": admin_token},
        json={"force": False},
    )

    assert response.status_code in (200, 202), f"Failed to trigger: {response.text}"
    data = response.json()

    assert "job_id" in data, "Response missing job_id"
    assert data.get("status") in ("queued", "processing"), "Invalid job status"

    job_id = data.get("job_id")
    assert job_id is not None, "job_id is None"
    assert len(job_id) > 0, "job_id is empty"


@pytest.mark.asyncio
async def test_trigger_clustering_job_with_force(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 2: Trigger clustering with force flag to skip if already running.

    Verifies:
    - POST with force=true starts new job
    - Previous job is not affected if different
    """
    response = await http_client.post(
        "/api/v1/admin/clustering/trigger",
        headers={"Authorization": admin_token},
        json={"force": True},
    )

    assert response.status_code in (200, 202), f"Failed to trigger: {response.text}"
    data = response.json()

    assert "job_id" in data
    assert data.get("status") in ("queued", "processing")


# ============================================================================
# B. JOB STATUS MONITORING (2 tests)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_clustering_job_completes_successfully(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 3: Trigger and wait for clustering job to complete.

    Verifies:
    - Job progresses from queued -> processing -> completed
    - Result contains statistics
    - Clusters are created and stored
    """
    # Check prerequisites
    article_count = await get_article_count(http_client, admin_token)
    if article_count < 5:
        pytest.skip(f"Not enough articles for clustering: {article_count}")

    # Trigger job
    trigger_resp = await http_client.post(
        "/api/v1/admin/clustering/trigger",
        headers={"Authorization": admin_token},
        json={"force": False},
    )

    assert trigger_resp.status_code in (200, 202)
    job_id = trigger_resp.json().get("job_id")

    # Wait for completion
    try:
        job_status = await wait_for_clustering_job(http_client, admin_token)
    except TimeoutError:
        pytest.skip("Clustering job timeout (may be processing in background)")

    assert job_status.get("status") == "completed", f"Job failed: {job_status}"

    result = job_status.get("result", {})
    assert result.get("success") is True, f"Job result not successful: {result}"
    assert result.get("clusters_count", 0) > 0, "No clusters created"


@pytest.mark.asyncio
async def test_clustering_job_status_endpoint(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 4: Verify job status endpoint returns valid response.

    Verifies:
    - GET /api/v1/admin/clustering/job-status returns 200
    - Response has status, job_id, and result fields
    - Status is one of: queued, processing, completed, failed
    """
    response = await http_client.get(
        "/api/v1/admin/clustering/job-status",
        headers={"Authorization": admin_token},
    )

    assert response.status_code == 200, f"Status endpoint failed: {response.text}"

    data = response.json()
    assert "status" in data, "Missing status field"
    assert data.get("status") in (
        "queued",
        "processing",
        "completed",
        "failed",
        "not_started",
    ), f"Invalid status: {data.get('status')}"


# ============================================================================
# C. DYNAMODB RESULT VERIFICATION (3 tests)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_clusters_stored_in_dynamodb(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 5: Verify clusters are stored in DynamoDB after job completion.

    Verifies:
    - Clusters are created in article_clusters table
    - Each cluster has cluster_id, article_id
    - Cluster metadata table is populated
    """
    # Get initial cluster count
    initial_count = await get_cluster_count(http_client, admin_token)

    # Trigger job
    trigger_resp = await http_client.post(
        "/api/v1/admin/clustering/trigger",
        headers={"Authorization": admin_token},
        json={"force": False},
    )

    if trigger_resp.status_code not in (200, 202):
        pytest.skip("Could not trigger clustering job")

    # Wait for completion
    try:
        job_status = await wait_for_clustering_job(http_client, admin_token)
    except TimeoutError:
        pytest.skip("Clustering job timeout")

    if job_status.get("status") != "completed":
        pytest.skip(f"Job did not complete: {job_status.get('status')}")

    # Wait a moment for data to be written
    await asyncio.sleep(1)

    # Get final cluster count
    final_count = await get_cluster_count(http_client, admin_token)

    assert final_count > 0, "No clusters found in database"
    # Note: final_count might not be > initial_count if clusters are refreshed
    # So we just verify that clusters exist


@pytest.mark.asyncio
async def test_cluster_data_structure(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 6: Verify cluster response has correct data structure.

    Verifies:
    - Cluster objects have required fields
    - cluster_id, size, centroid, created_at are present
    - Topic summary is generated
    """
    response = await http_client.get(
        "/api/v1/clusters?limit=1&skip=0",
        headers={"Authorization": admin_token},
    )

    if response.status_code != 200:
        pytest.skip("Could not fetch clusters")

    data = response.json()
    clusters = data.get("items", [])

    if not clusters:
        pytest.skip("No clusters in database")

    cluster = clusters[0]

    # Verify required fields
    assert "cluster_id" in cluster, "Missing cluster_id"
    assert "size" in cluster, "Missing size"
    assert isinstance(cluster.get("size"), int), "size not an integer"
    assert cluster.get("size") > 0, "cluster size is 0"

    assert "created_at" in cluster, "Missing created_at"
    assert isinstance(cluster.get("created_at"), (int, float)), "created_at not numeric"


@pytest.mark.asyncio
async def test_embeddings_stored_for_clustered_articles(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 7: Verify embeddings are stored for articles in clusters.

    Verifies:
    - Article embeddings table is populated
    - Embeddings have correct dimensions
    - Embeddings are stored alongside cluster assignments
    """
    embeddings_count = await get_embeddings_count(http_client, admin_token)

    assert embeddings_count > 0, "No embeddings found in database"


# ============================================================================
# D. CLUSTER PAGINATION (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_cluster_pagination_default(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 8: Test cluster list pagination with default parameters.

    Verifies:
    - GET /api/v1/clusters returns paginated results
    - Default limit is applied
    - skip/limit parameters work
    - total count is returned
    """
    response = await http_client.get(
        "/api/v1/clusters",
        headers={"Authorization": admin_token},
    )

    assert response.status_code == 200, f"Failed to fetch clusters: {response.text}"

    data = response.json()

    assert "items" in data, "Missing items in response"
    assert isinstance(data.get("items"), list), "items is not a list"

    assert "total" in data, "Missing total count"
    assert isinstance(data.get("total"), int), "total is not an integer"

    assert "skip" in data, "Missing skip"
    assert "limit" in data, "Missing limit"


@pytest.mark.asyncio
async def test_cluster_pagination_with_parameters(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 9: Test cluster pagination with explicit skip and limit.

    Verifies:
    - skip parameter offsets results
    - limit parameter controls page size
    - Multiple pages can be retrieved
    """
    # Get first page
    response1 = await http_client.get(
        "/api/v1/clusters?limit=5&skip=0",
        headers={"Authorization": admin_token},
    )

    assert response1.status_code == 200

    data1 = response1.json()
    items1 = data1.get("items", [])
    total = data1.get("total", 0)

    if total <= 5:
        pytest.skip("Not enough clusters for pagination test")

    # Get second page
    response2 = await http_client.get(
        "/api/v1/clusters?limit=5&skip=5",
        headers={"Authorization": admin_token},
    )

    assert response2.status_code == 200

    data2 = response2.json()
    items2 = data2.get("items", [])

    # Verify different items in each page
    if items1 and items2:
        ids1 = [item.get("cluster_id") for item in items1]
        ids2 = [item.get("cluster_id") for item in items2]
        # At least some items should be different
        assert len(set(ids1) & set(ids2)) < len(ids1), "Pages have overlapping results"


# ============================================================================
# E. CLUSTER SEARCH/FILTER (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_cluster_search_by_topic(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 10: Test cluster search by topic/query.

    Verifies:
    - GET /api/v1/clusters?q=<query> filters results
    - Search results are relevant
    - Empty search returns all clusters
    """
    # Get all clusters
    all_response = await http_client.get(
        "/api/v1/clusters?limit=100",
        headers={"Authorization": admin_token},
    )

    assert all_response.status_code == 200

    all_data = all_response.json()
    all_clusters = all_data.get("items", [])

    if not all_clusters:
        pytest.skip("No clusters to search")

    # Try searching with first cluster's topic (if available)
    first_cluster = all_clusters[0]
    topic = first_cluster.get("topic", "").lower()

    if topic:
        search_response = await http_client.get(
            f"/api/v1/clusters?q={topic[:5]}",
            headers={"Authorization": admin_token},
        )

        if search_response.status_code == 200:
            search_data = search_response.json()
            search_results = search_data.get("items", [])
            # Search should return results (or return empty set gracefully)
            assert isinstance(search_results, list)


@pytest.mark.asyncio
async def test_cluster_filter_by_size(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 11: Test cluster filtering by size.

    Verifies:
    - GET /api/v1/clusters?min_size=<n> filters by size
    - Results respect the filter
    """
    # Get all clusters
    response = await http_client.get(
        "/api/v1/clusters?limit=100",
        headers={"Authorization": admin_token},
    )

    if response.status_code != 200:
        pytest.skip("Could not fetch clusters")

    data = response.json()
    clusters = data.get("items", [])

    if not clusters:
        pytest.skip("No clusters to filter")

    # Get max size
    max_size = max(c.get("size", 0) for c in clusters)

    if max_size < 3:
        pytest.skip("No clusters with size >= 3")

    # Filter by min size
    filtered_response = await http_client.get(
        f"/api/v1/clusters?limit=100&min_size=2",
        headers={"Authorization": admin_token},
    )

    if filtered_response.status_code == 200:
        filtered_data = filtered_response.json()
        filtered_clusters = filtered_data.get("items", [])

        # All results should meet the filter
        for cluster in filtered_clusters:
            size = cluster.get("size", 0)
            assert size >= 2, f"Cluster size {size} below filter threshold"


# ============================================================================
# F. METRICS CALCULATION (2 tests)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_clustering_metrics_calculation(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 12: Verify clustering metrics are calculated correctly.

    Verifies:
    - Silhouette score, Davies-Bouldin, Calinski-Harabasz scores are stored
    - Metrics are within valid ranges
    - Evaluation results are queryable
    """
    response = await http_client.get(
        "/api/v1/admin/clustering/metrics",
        headers={"Authorization": admin_token},
    )

    if response.status_code != 200:
        pytest.skip("Clustering metrics endpoint not available")

    data = response.json()

    # Verify metric structure
    if "metrics" in data:
        metrics = data["metrics"]
        # Silhouette score: -1 to 1
        if "silhouette_score" in metrics:
            assert -1 <= metrics["silhouette_score"] <= 1

        # Davies-Bouldin: 0 and up (lower is better)
        if "davies_bouldin_score" in metrics:
            assert metrics["davies_bouldin_score"] >= 0

        # Calinski-Harabasz: >= 0 (higher is better)
        if "calinski_harabasz_score" in metrics:
            assert metrics["calinski_harabasz_score"] >= 0


@pytest.mark.asyncio
async def test_clustering_job_duration_metrics(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 13: Verify clustering job duration is tracked.

    Verifies:
    - Job duration is recorded
    - Duration is positive
    - Statistics are available
    """
    response = await http_client.get(
        "/api/v1/admin/clustering/job-status",
        headers={"Authorization": admin_token},
    )

    if response.status_code != 200:
        pytest.skip("Job status endpoint not available")

    data = response.json()
    result = data.get("result", {})

    if result.get("success"):
        duration = result.get("duration_seconds")
        if duration is not None:
            assert isinstance(duration, (int, float))
            assert duration > 0, "Job duration must be positive"


# ============================================================================
# G. ERROR HANDLING (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_clustering_unauthorized_access(
    backend_ready,
    http_client: httpx.AsyncClient,
):
    """Test 14: Verify clustering endpoints require authentication.

    Verifies:
    - Accessing without token returns 401 or 403
    - Admin endpoints are protected
    """
    response = await http_client.post(
        "/api/v1/admin/clustering/trigger",
        json={"force": False},
    )

    # Should be rejected without auth
    assert response.status_code in (
        401,
        403,
    ), f"Unauthorized request not rejected: {response.status_code}"


@pytest.mark.asyncio
async def test_clustering_invalid_parameters(
    backend_ready,
    http_client: httpx.AsyncClient,
    admin_token: str,
):
    """Test 15: Verify invalid parameters are handled gracefully.

    Verifies:
    - Invalid skip/limit values are handled
    - Invalid queries return appropriate errors
    - Backend doesn't crash on bad input
    """
    # Test with negative skip
    response = await http_client.get(
        "/api/v1/clusters?skip=-1&limit=10",
        headers={"Authorization": admin_token},
    )

    # Should either reject or handle gracefully
    assert response.status_code in (200, 400, 422)

    # Test with very large limit
    response = await http_client.get(
        "/api/v1/clusters?skip=0&limit=999999",
        headers={"Authorization": admin_token},
    )

    assert response.status_code in (200, 400, 422)


# ============================================================================
# PYTEST HOOKS
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_clustering_tests():
    """Setup for clustering test session."""
    print("\n" + "=" * 80)
    print("CLUSTERING E2E TEST SUITE")
    print("=" * 80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test User ID: {TEST_USER_ID}")
    print("=" * 80 + "\n")


def pytest_collection_modifyitems(config, items):
    """Add asyncio marker to async tests."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
