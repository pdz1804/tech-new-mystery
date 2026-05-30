"""Unit and integration tests for admin clustering evaluation endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.clustering import ClusteringEvaluationModel, EvaluationResultItem


# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture
def mock_evaluation_model():
    """Create a mock ClusteringEvaluationModel for testing."""
    model = MagicMock(spec=ClusteringEvaluationModel)
    model.evaluation_id = "eval-2026-05-28-18-00"
    model.timestamp = 1717008000
    model.evaluation_type = "manual"
    model.total_articles_evaluated = 500
    model.selected_k_value = 6
    model.best_composite_score = 0.542
    model.quality_threshold_met = True
    model.completed_at = 1717008342

    # Create mock admin weights
    admin_weights = MagicMock()
    admin_weights.silhouette_weight = 0.5
    admin_weights.davies_bouldin_weight = 0.3
    admin_weights.calinski_harabasz_weight = 0.2
    model.admin_weights = admin_weights

    # Create mock evaluation results (for k=6, the selected one)
    result_item = MagicMock(spec=EvaluationResultItem)
    result_item.k_value = 6
    result_item.silhouette_score = 0.51
    result_item.davies_bouldin_index = 1.6
    result_item.calinski_harabasz_index = 312.8
    result_item.silhouette_rank = 8
    result_item.davies_bouldin_rank = 5
    result_item.calinski_harabasz_rank = 18
    result_item.weighted_composite_score = 0.542
    result_item.num_clusters_formed = 6
    result_item.avg_cluster_size = 16.8
    result_item.noise_percentage = 2.1
    result_item.evaluation_time_ms = 241

    model.evaluation_results = [result_item]

    # Create mock metrics summary
    metrics_summary = {
        "silhouette_score": {
            "min": 0.08,
            "max": 0.51,
            "mean": 0.32,
            "std_dev": 0.11,
        },
        "davies_bouldin_index": {
            "min": 1.2,
            "max": 4.8,
            "mean": 2.1,
            "std_dev": 0.9,
        },
        "calinski_harabasz_index": {
            "min": 85.2,
            "max": 425.6,
            "mean": 248.3,
            "std_dev": 92.1,
        },
        "composite_score": {
            "min": 0.008,
            "max": 0.542,
            "mean": 0.185,
            "std_dev": 0.131,
        },
    }
    model.metrics_summary = metrics_summary

    return model


@pytest.fixture
def mock_evaluation_list():
    """Create multiple mock evaluation models for list testing."""
    evaluations = []

    for i in range(5):
        model = MagicMock(spec=ClusteringEvaluationModel)
        model.evaluation_id = f"eval-2026-05-28-{18-i}:00"
        model.timestamp = 1717008000 - (i * 3600)
        model.evaluation_type = "scheduled" if i % 2 == 0 else "manual"
        model.total_articles_evaluated = 500 - (i * 50)
        model.selected_k_value = 5 + i
        model.best_composite_score = 0.542 - (i * 0.05)
        model.quality_threshold_met = True if model.best_composite_score > 0.3 else False

        # Create mock result
        result_item = MagicMock(spec=EvaluationResultItem)
        result_item.k_value = model.selected_k_value
        result_item.silhouette_score = 0.51 - (i * 0.05)
        result_item.davies_bouldin_index = 1.6 + (i * 0.2)
        result_item.calinski_harabasz_index = 312.8 - (i * 30)
        result_item.weighted_composite_score = model.best_composite_score

        model.evaluation_results = [result_item]
        evaluations.append(model)

    return evaluations


# ============================================================
# Tests: GET /v1/admin/clustering/evaluations (List)
# ============================================================


@pytest.mark.asyncio
async def test_list_evaluations_success(client, mock_evaluation_list):
    """Test successful list of evaluations with pagination."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_latest_evaluations",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_evaluation_list

        # Mock require_admin to allow request
        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            response = client.get(
                "/v1/admin/clustering/evaluations?limit=3&offset=0",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 3
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["limit"] == 3
        assert data["pagination"]["offset"] == 0

        # Verify first item structure
        first_item = data["items"][0]
        assert "evaluation_id" in first_item
        assert "timestamp" in first_item
        assert "num_articles" in first_item
        assert "num_clusters" in first_item
        assert "weighted_score" in first_item
        assert "quality_threshold_met" in first_item


@pytest.mark.asyncio
async def test_list_evaluations_pagination(client, mock_evaluation_list):
    """Test pagination works correctly."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_latest_evaluations",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_evaluation_list

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            # Request page 2
            response = client.get(
                "/v1/admin/clustering/evaluations?limit=2&offset=2",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 200
        data = response.json()

        # Should return items 3 and 4 (0-indexed)
        assert len(data["items"]) == 2
        assert data["pagination"]["offset"] == 2
        assert data["pagination"]["limit"] == 2


@pytest.mark.asyncio
async def test_list_evaluations_empty(client):
    """Test list returns empty when no evaluations exist."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_latest_evaluations",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = []

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            response = client.get(
                "/v1/admin/clustering/evaluations",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["pagination"]["total"] == 0


# ============================================================
# Tests: GET /v1/admin/clustering/evaluations/{evaluation_id}
# ============================================================


@pytest.mark.asyncio
async def test_get_evaluation_detail_success(client, mock_evaluation_model):
    """Test successful retrieval of evaluation details."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_evaluation_by_id",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_evaluation_model

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            response = client.get(
                "/v1/admin/clustering/evaluations/eval-2026-05-28-18-00",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["evaluation_id"] == "eval-2026-05-28-18-00"
        assert data["timestamp"] == 1717008000
        assert data["evaluation_type"] == "manual"
        assert data["total_articles_evaluated"] == 500
        assert data["selected_k_value"] == 6
        assert data["best_composite_score"] == 0.542
        assert data["quality_threshold_met"] is True

        # Verify admin weights
        assert "admin_weights" in data
        assert data["admin_weights"]["silhouette_weight"] == 0.5

        # Verify evaluation results
        assert "evaluation_results" in data
        assert len(data["evaluation_results"]) > 0
        result = data["evaluation_results"][0]
        assert result["k_value"] == 6
        assert result["silhouette_score"] == 0.51

        # Verify metrics summary
        assert "metrics_summary" in data
        assert "silhouette_score" in data["metrics_summary"]


@pytest.mark.asyncio
async def test_get_evaluation_detail_not_found(client):
    """Test that 404 is returned when evaluation not found."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_evaluation_by_id",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            response = client.get(
                "/v1/admin/clustering/evaluations/eval-nonexistent",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


# ============================================================
# Tests: DELETE /v1/admin/clustering/evaluations/{evaluation_id}
# ============================================================


@pytest.mark.asyncio
async def test_delete_evaluation_success(client):
    """Test successful deletion of evaluation."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.delete_evaluation",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = True

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            response = client.delete(
                "/v1/admin/clustering/evaluations/eval-2026-05-28-18-00",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 204  # No Content


@pytest.mark.asyncio
async def test_delete_evaluation_not_found(client):
    """Test that 404 is returned when evaluation to delete not found."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.delete_evaluation",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = False

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            response = client.delete(
                "/v1/admin/clustering/evaluations/eval-nonexistent",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


# ============================================================
# Tests: POST /v1/admin/clustering/evaluations/trigger
# ============================================================


@pytest.mark.asyncio
async def test_trigger_evaluation_success(client):
    """Test successful manual evaluation trigger."""
    mock_task = MagicMock()
    mock_task.id = "task-123-abc"

    with patch(
        "app.workers.tasks.evaluation_tasks.evaluate_clustering_quality.delay",
        return_value=mock_task,
    ) as mock_delay:
        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            response = client.post(
                "/v1/admin/clustering/evaluations/trigger",
                json={"trigger_reason": "Manual quality check"},
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "task-123-abc"
        assert data["status"] == "queued"

        # Verify the task was queued with correct parameters
        mock_delay.assert_called_once()
        call_kwargs = mock_delay.call_args[1]
        assert call_kwargs["trigger_reason"] == "Manual quality check"


@pytest.mark.asyncio
async def test_trigger_evaluation_invalid_request(client):
    """Test that invalid request body is rejected."""
    with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
        response = client.post(
            "/v1/admin/clustering/evaluations/trigger",
            json={"trigger_reason": ""},  # Empty reason should fail validation
            headers={"Authorization": "Bearer mock-token"},
        )

    # Should fail validation
    assert response.status_code == 422


# ============================================================
# Integration Tests
# ============================================================


@pytest.mark.asyncio
async def test_full_workflow_list_then_detail(client, mock_evaluation_list, mock_evaluation_model):
    """Test full workflow: list evaluations, then get one detail."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_latest_evaluations",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = mock_evaluation_list

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            # First: list evaluations
            list_response = client.get(
                "/v1/admin/clustering/evaluations?limit=5&offset=0",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data["items"]) == 5

        # Extract ID from first item
        eval_id = list_data["items"][0]["evaluation_id"]

    # Second: get detail of first evaluation
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_evaluation_by_id",
        new_callable=AsyncMock,
    ) as mock_detail:
        mock_detail.return_value = mock_evaluation_model

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            detail_response = client.get(
                f"/v1/admin/clustering/evaluations/{eval_id}",
                headers={"Authorization": "Bearer mock-token"},
            )

    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data["evaluation_id"] == mock_evaluation_model.evaluation_id


@pytest.mark.asyncio
async def test_pagination_offset_bounds(client, mock_evaluation_list):
    """Test pagination with edge case offsets."""
    with patch(
        "app.repositories.clustering_evaluation_repository.ClusteringEvaluationRepository.get_latest_evaluations",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_evaluation_list

        with patch("app.api.dependencies.require_admin", return_value={"user_id": "admin-1"}):
            # Request with offset >= total
            response = client.get(
                "/v1/admin/clustering/evaluations?limit=10&offset=100",
                headers={"Authorization": "Bearer mock-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0  # No items beyond offset
