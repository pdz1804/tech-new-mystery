"""Unit tests for visualization_service.py"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.visualization_service import VisualizationService
from app.models.clustering import (
    ClusteringEvaluationModel,
    EvaluationResultItem,
)


@pytest.fixture
def visualization_service():
    """Create VisualizationService with mocked repository."""
    repo = AsyncMock()
    return VisualizationService(evaluation_repo=repo)


@pytest.fixture
def mock_evaluation_result():
    """Create a mock evaluation result item."""
    return EvaluationResultItem(
        k_value=10,
        silhouette_score=0.65,
        davies_bouldin_index=1.5,
        calinski_harabasz_index=350.0,
        silhouette_rank=5,
        davies_bouldin_rank=3,
        calinski_harabasz_rank=8,
        weighted_composite_score=0.45,
        num_clusters_formed=10,
        avg_cluster_size=25.3,
        noise_percentage=2.5,
        evaluation_time_ms=234.5,
    )


@pytest.fixture
def mock_evaluation(mock_evaluation_result):
    """Create a mock clustering evaluation."""
    evaluation = Mock(spec=ClusteringEvaluationModel)
    evaluation.evaluation_id = "eval-2026-05-29-10-00"
    evaluation.timestamp = 1717003200  # Unix timestamp
    evaluation.evaluation_type = "scheduled"
    evaluation.selected_k_value = 10
    evaluation.best_composite_score = 0.45
    evaluation.total_articles_evaluated = 250
    evaluation.evaluation_results = [mock_evaluation_result]
    evaluation.admin_weights = {
        "silhouette_weight": 0.5,
        "davies_bouldin_weight": 0.3,
        "calinski_harabasz_weight": 0.2,
    }
    evaluation.quality_threshold_met = True
    return evaluation


class TestVisualizationServiceNormalization:
    """Test normalization logic."""

    def test_normalize_silhouette_identity(self, visualization_service):
        """Silhouette should remain unchanged (already 0-1)."""
        params = {
            "silhouette_min": 0.0,
            "silhouette_max": 1.0,
            "davies_bouldin_min": 0.8,
            "davies_bouldin_max": 3.2,
            "calinski_harabasz_p25": 150.0,
            "calinski_harabasz_p75": 450.0,
            "calinski_harabasz_min": 50.0,
            "calinski_harabasz_max": 500.0,
        }

        result = visualization_service._normalize_metrics(0.65, 1.5, 350.0, params)

        # Silhouette should be unchanged
        assert result[0] == pytest.approx(0.65, abs=0.01)
        assert 0.0 <= result[0] <= 1.0

    def test_normalize_davies_bouldin_inverted(self, visualization_service):
        """Davies-Bouldin should be inverted (lower scores become higher)."""
        params = {
            "silhouette_min": 0.0,
            "silhouette_max": 1.0,
            "davies_bouldin_min": 1.0,
            "davies_bouldin_max": 3.0,
            "calinski_harabasz_p25": 150.0,
            "calinski_harabasz_p75": 450.0,
            "calinski_harabasz_min": 50.0,
            "calinski_harabasz_max": 500.0,
        }

        # Score of 1.5 is in middle of range [1.0, 3.0]
        # Normalized: (1.5 - 1.0) / (3.0 - 1.0) = 0.25
        # Inverted: 1.0 - 0.25 = 0.75
        result = visualization_service._normalize_metrics(0.5, 1.5, 300.0, params)

        davies_bouldin_norm = result[1]
        assert 0.7 <= davies_bouldin_norm <= 0.8  # Should be ~0.75
        assert 0.0 <= davies_bouldin_norm <= 1.0

    def test_normalize_davies_bouldin_clipping(self, visualization_service):
        """Davies-Bouldin outside range should be clipped."""
        params = {
            "silhouette_min": 0.0,
            "silhouette_max": 1.0,
            "davies_bouldin_min": 1.0,
            "davies_bouldin_max": 3.0,
            "calinski_harabasz_p25": 150.0,
            "calinski_harabasz_p75": 450.0,
            "calinski_harabasz_min": 50.0,
            "calinski_harabasz_max": 500.0,
        }

        # Very high Davies-Bouldin (worse clustering)
        result_high = visualization_service._normalize_metrics(0.5, 5.0, 300.0, params)
        # Very low Davies-Bouldin (better clustering)
        result_low = visualization_service._normalize_metrics(0.5, 0.5, 300.0, params)

        # High should be low normalized (after inversion)
        # Low should be high normalized (after inversion)
        assert result_high[1] < result_low[1]

    def test_normalize_calinski_harabasz_percentile(self, visualization_service):
        """Calinski-Harabasz should use percentile normalization."""
        params = {
            "silhouette_min": 0.0,
            "silhouette_max": 1.0,
            "davies_bouldin_min": 1.0,
            "davies_bouldin_max": 3.0,
            "calinski_harabasz_p25": 150.0,
            "calinski_harabasz_p75": 450.0,
            "calinski_harabasz_min": 50.0,
            "calinski_harabasz_max": 500.0,
        }

        # Value at p50 (middle)
        result = visualization_service._normalize_metrics(0.5, 1.5, 300.0, params)

        ch_norm = result[2]
        # (300 - 150) / (450 - 150) = 150 / 300 = 0.5
        assert 0.49 <= ch_norm <= 0.51
        assert 0.0 <= ch_norm <= 1.0

    def test_normalize_metrics_all_in_range(self, visualization_service):
        """All normalized values should be in [0, 1]."""
        params = {
            "silhouette_min": 0.0,
            "silhouette_max": 1.0,
            "davies_bouldin_min": 0.5,
            "davies_bouldin_max": 5.0,
            "calinski_harabasz_p25": 100.0,
            "calinski_harabasz_p75": 500.0,
            "calinski_harabasz_min": 50.0,
            "calinski_harabasz_max": 600.0,
        }

        # Test various metric combinations
        test_cases = [
            (0.3, 2.0, 250.0),
            (0.7, 1.0, 400.0),
            (0.5, 4.0, 50.0),
            (0.0, 5.5, 700.0),
            (1.0, -0.5, 0.0),
        ]

        for silhouette, davies_bouldin, calinski_harabasz in test_cases:
            result = visualization_service._normalize_metrics(
                silhouette, davies_bouldin, calinski_harabasz, params
            )

            assert len(result) == 3
            for normalized_value in result:
                assert 0.0 <= normalized_value <= 1.0, \
                    f"Value {normalized_value} out of range for input " \
                    f"({silhouette}, {davies_bouldin}, {calinski_harabasz})"


class TestVisualizationServiceNormalizationParams:
    """Test normalization parameter calculation."""

    def test_calculate_normalization_params_silhouette(self, visualization_service):
        """Silhouette params should be fixed 0-1 range."""
        silhouette_scores = [0.3, 0.5, 0.7, 0.8, 0.6]
        davies_bouldin = [1.0, 2.0, 1.5]
        calinski_harabasz = [100.0, 200.0, 150.0]

        params = visualization_service._calculate_normalization_params(
            silhouette_scores, davies_bouldin, calinski_harabasz
        )

        assert params["silhouette_min"] == 0.0
        assert params["silhouette_max"] == 1.0

    def test_calculate_normalization_params_davies_bouldin(self, visualization_service):
        """Davies-Bouldin params should track min/max."""
        silhouette_scores = [0.5] * 3
        davies_bouldin = [0.8, 2.5, 1.2]
        calinski_harabasz = [150.0] * 3

        params = visualization_service._calculate_normalization_params(
            silhouette_scores, davies_bouldin, calinski_harabasz
        )

        assert params["davies_bouldin_min"] == pytest.approx(0.8)
        assert params["davies_bouldin_max"] == pytest.approx(2.5)

    def test_calculate_normalization_params_calinski_percentile(self, visualization_service):
        """Calinski-Harabasz params should use percentiles."""
        silhouette_scores = [0.5] * 100
        davies_bouldin = [1.5] * 100
        calinski_harabasz = list(range(50, 550))  # 50 to 549

        params = visualization_service._calculate_normalization_params(
            silhouette_scores, davies_bouldin, calinski_harabasz
        )

        # 25th percentile of [50...549] is around 175
        # 75th percentile is around 425
        assert 170 <= params["calinski_harabasz_p25"] <= 180
        assert 420 <= params["calinski_harabasz_p75"] <= 430

    def test_calculate_normalization_params_empty_lists(self, visualization_service):
        """Should handle empty metric lists gracefully."""
        params = visualization_service._calculate_normalization_params([], [], [])

        # Should have default values
        assert "silhouette_min" in params
        assert "davies_bouldin_min" in params
        assert "calinski_harabasz_p25" in params


class TestVisualizationServiceGetMetrics:
    """Test main visualization data generation."""

    @pytest.mark.asyncio
    async def test_get_metrics_visualization_basic(self, visualization_service, mock_evaluation):
        """Should generate visualization data from evaluations."""
        visualization_service._evaluation_repo.get_latest_evaluations.return_value = [
            mock_evaluation
        ]

        result = await visualization_service.get_metrics_visualization(limit=5)

        # Verify response structure
        assert result["plot_type"] == "radar"
        assert result["axes"] == [
            "silhouette_score",
            "davies_bouldin_index",
            "calinski_harabasz_index",
        ]
        assert "datasets" in result
        assert "thresholds" in result

    @pytest.mark.asyncio
    async def test_get_metrics_visualization_datasets(self, visualization_service, mock_evaluation):
        """Should format datasets correctly."""
        visualization_service._evaluation_repo.get_latest_evaluations.return_value = [
            mock_evaluation
        ]

        result = await visualization_service.get_metrics_visualization(limit=5)

        datasets = result["datasets"]
        assert len(datasets) == 1

        dataset = datasets[0]
        assert "label" in dataset
        assert "data" in dataset  # Normalized values
        assert "timestamp" in dataset
        assert "selected_k" in dataset
        assert "raw_values" in dataset

        # Data should have 3 values
        assert len(dataset["data"]) == 3
        # All normalized values should be in [0, 1]
        for value in dataset["data"]:
            assert 0.0 <= value <= 1.0

    @pytest.mark.asyncio
    async def test_get_metrics_visualization_thresholds(self, visualization_service, mock_evaluation):
        """Should include normalized thresholds."""
        visualization_service._evaluation_repo.get_latest_evaluations.return_value = [
            mock_evaluation
        ]

        result = await visualization_service.get_metrics_visualization(limit=5)

        thresholds = result["thresholds"]
        assert "raw" in thresholds
        assert "normalized" in thresholds

        assert thresholds["raw"]["silhouette_score"] == 0.5
        assert thresholds["raw"]["davies_bouldin_index"] == 1.5
        assert thresholds["raw"]["calinski_harabasz_index"] == 50

        # Normalized thresholds should be in range
        for value in thresholds["normalized"]:
            assert 0.0 <= value <= 1.0

    @pytest.mark.asyncio
    async def test_get_metrics_visualization_no_data(self, visualization_service):
        """Should return empty response when no evaluations found."""
        visualization_service._evaluation_repo.get_latest_evaluations.return_value = []

        result = await visualization_service.get_metrics_visualization(limit=5)

        assert result["datasets"] == []
        assert result["plot_type"] == "radar"

    @pytest.mark.asyncio
    async def test_get_metrics_visualization_limit_clamping(self, visualization_service, mock_evaluation):
        """Should clamp limit to valid range."""
        visualization_service._evaluation_repo.get_latest_evaluations.return_value = [
            mock_evaluation
        ]

        # Test limit too low
        result = await visualization_service.get_metrics_visualization(limit=0)
        visualization_service._evaluation_repo.get_latest_evaluations.assert_called_with(limit=1)

        # Reset mock
        visualization_service._evaluation_repo.get_latest_evaluations.reset_mock()
        visualization_service._evaluation_repo.get_latest_evaluations.return_value = [
            mock_evaluation
        ]

        # Test limit too high
        result = await visualization_service.get_metrics_visualization(limit=100)
        visualization_service._evaluation_repo.get_latest_evaluations.assert_called_with(limit=20)

    @pytest.mark.asyncio
    async def test_get_metrics_visualization_multiple_evaluations(self, visualization_service):
        """Should handle multiple evaluations."""
        eval1 = Mock(spec=ClusteringEvaluationModel)
        eval1.evaluation_id = "eval-1"
        eval1.timestamp = 1717003200
        eval1.selected_k_value = 8
        eval1.best_composite_score = 0.42
        eval1.evaluation_results = [Mock(
            k_value=8,
            silhouette_score=0.62,
            davies_bouldin_index=1.6,
            calinski_harabasz_index=330.0,
        )]

        eval2 = Mock(spec=ClusteringEvaluationModel)
        eval2.evaluation_id = "eval-2"
        eval2.timestamp = 1717006800
        eval2.selected_k_value = 10
        eval2.best_composite_score = 0.45
        eval2.evaluation_results = [Mock(
            k_value=10,
            silhouette_score=0.65,
            davies_bouldin_index=1.5,
            calinski_harabasz_index=350.0,
        )]

        visualization_service._evaluation_repo.get_latest_evaluations.return_value = [
            eval2, eval1  # Latest first
        ]

        result = await visualization_service.get_metrics_visualization(limit=5)

        datasets = result["datasets"]
        assert len(datasets) == 2
        # Most recent should be first
        assert datasets[0]["timestamp"] > datasets[1]["timestamp"]

    @pytest.mark.asyncio
    async def test_get_metrics_visualization_error_handling(self, visualization_service):
        """Should handle repository errors gracefully."""
        visualization_service._evaluation_repo.get_latest_evaluations.side_effect = Exception(
            "Database connection error"
        )

        with pytest.raises(Exception, match="Database connection error"):
            await visualization_service.get_metrics_visualization(limit=5)
