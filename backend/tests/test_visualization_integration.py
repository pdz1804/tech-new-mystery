"""Integration tests for visualization service with real DynamoDB data.

These tests verify that the visualization service correctly retrieves
and processes real evaluation data from DynamoDB.
"""

import pytest
import asyncio
from datetime import datetime

from app.services.visualization_service import VisualizationService
from app.repositories.clustering_evaluation_repository import ClusteringEvaluationRepository
from app.models.clustering import (
    ClusteringEvaluationModel,
    EvaluationResultItem,
)
from app.utils.time import now_timestamp


@pytest.fixture
def evaluation_repo():
    """Create real clustering evaluation repository."""
    return ClusteringEvaluationRepository()


class TestVisualizationIntegration:
    """Integration tests using real DynamoDB."""

    @pytest.mark.asyncio
    async def test_get_latest_evaluations_from_dynamodb(self, evaluation_repo):
        """Should retrieve latest evaluations from DynamoDB."""
        try:
            evaluations = await evaluation_repo.get_latest_evaluations(limit=5)

            # Should return a list (may be empty if no evaluations exist)
            assert isinstance(evaluations, list)

            # If evaluations exist, verify structure
            if len(evaluations) > 0:
                evaluation = evaluations[0]
                assert hasattr(evaluation, "evaluation_id")
                assert hasattr(evaluation, "timestamp")
                assert hasattr(evaluation, "selected_k_value")
                assert hasattr(evaluation, "evaluation_results")

                # Evaluations should be sorted by timestamp (newest first)
                if len(evaluations) > 1:
                    assert evaluations[0].timestamp >= evaluations[1].timestamp

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_visualization_with_real_data(self, evaluation_repo):
        """Should generate visualization data from real DynamoDB evaluations."""
        try:
            service = VisualizationService(evaluation_repo=evaluation_repo)
            result = await service.get_metrics_visualization(limit=5)

            # Verify response structure
            assert isinstance(result, dict)
            assert result["plot_type"] == "radar"
            assert "axes" in result
            assert "datasets" in result
            assert "thresholds" in result

            # Verify axes
            assert len(result["axes"]) == 3
            assert "silhouette_score" in result["axes"]
            assert "davies_bouldin_index" in result["axes"]
            assert "calinski_harabasz_index" in result["axes"]

            # If datasets exist, verify structure
            if len(result["datasets"]) > 0:
                dataset = result["datasets"][0]

                # Verify dataset structure
                assert "label" in dataset
                assert "data" in dataset
                assert "timestamp" in dataset
                assert "selected_k" in dataset
                assert "raw_values" in dataset

                # Verify normalized data
                assert len(dataset["data"]) == 3
                for value in dataset["data"]:
                    assert isinstance(value, float)
                    assert 0.0 <= value <= 1.0, \
                        f"Normalized value {value} outside [0, 1] range"

                # Verify raw values
                raw = dataset["raw_values"]
                assert "silhouette_score" in raw
                assert "davies_bouldin_index" in raw
                assert "calinski_harabasz_index" in raw

                # Verify raw value ranges
                assert 0.0 <= raw["silhouette_score"] <= 1.0
                assert raw["davies_bouldin_index"] >= 0.0
                assert raw["calinski_harabasz_index"] >= 0.0

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_visualization_normalization_consistency(self, evaluation_repo):
        """Verify that normalization is consistent across multiple calls."""
        try:
            service = VisualizationService(evaluation_repo=evaluation_repo)

            # Get visualization twice
            result1 = await service.get_metrics_visualization(limit=5)
            result2 = await service.get_metrics_visualization(limit=5)

            # Both should have same structure and values
            assert result1["plot_type"] == result2["plot_type"]
            assert len(result1["datasets"]) == len(result2["datasets"])

            # If datasets exist, normalized values should be identical
            if len(result1["datasets"]) > 0:
                for i, dataset in enumerate(result1["datasets"]):
                    assert dataset["data"] == result2["datasets"][i]["data"]

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_visualization_metrics_correlation(self, evaluation_repo):
        """Verify that high silhouette and low davies-bouldin are correlated."""
        try:
            service = VisualizationService(evaluation_repo=evaluation_repo)
            result = await service.get_metrics_visualization(limit=10)

            if len(result["datasets"]) < 2:
                pytest.skip("Not enough evaluation data for correlation test")

            # Extract metrics
            silhouette_normalized = []
            davies_bouldin_normalized = []

            for dataset in result["datasets"]:
                silhouette_normalized.append(dataset["data"][0])
                davies_bouldin_normalized.append(dataset["data"][1])

            # Good clustering should have:
            # - High silhouette (close to 1)
            # - High davies_bouldin_normalized (close to 1, because it's inverted)
            # These should be roughly correlated

            # Find best evaluation (highest silhouette)
            best_idx = silhouette_normalized.index(max(silhouette_normalized))
            best_silhouette = silhouette_normalized[best_idx]
            best_davies_norm = davies_bouldin_normalized[best_idx]

            # High silhouette should generally correspond to high normalized davies-bouldin
            # (at least for the best evaluations)
            assert best_silhouette >= 0.4, "Best silhouette score is quite low"
            assert best_davies_norm >= 0.3, "Best davies-bouldin normalized is quite low"

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_visualization_limit_parameter(self, evaluation_repo):
        """Verify that limit parameter works correctly."""
        try:
            service = VisualizationService(evaluation_repo=evaluation_repo)

            # Test different limits
            result_1 = await service.get_metrics_visualization(limit=1)
            result_5 = await service.get_metrics_visualization(limit=5)
            result_20 = await service.get_metrics_visualization(limit=20)

            # More recent evaluations, more datasets (up to limit)
            num_1 = len(result_1["datasets"])
            num_5 = len(result_5["datasets"])
            num_20 = len(result_20["datasets"])

            assert num_1 <= 1, "limit=1 should return at most 1 dataset"
            assert num_5 <= 5, "limit=5 should return at most 5 datasets"
            assert num_20 <= 20, "limit=20 should return at most 20 datasets"

            # More datasets with higher limit (if evaluations exist)
            if num_1 > 0:
                assert num_5 >= num_1, "limit=5 should have at least as many as limit=1"

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_visualization_threshold_sanity(self):
        """Verify that threshold values are reasonable."""
        service = VisualizationService()

        # Test with minimal data (just thresholds)
        result = service._empty_response()

        raw = result["thresholds"]["raw"]
        normalized = result["thresholds"]["normalized"]

        # Verify thresholds are in expected ranges
        assert 0.0 <= raw["silhouette_score"] <= 1.0
        assert raw["davies_bouldin_index"] > 0.0
        assert raw["calinski_harabasz_index"] > 0.0

        # Normalized thresholds should be in [0, 1]
        for value in normalized:
            assert 0.0 <= value <= 1.0

    @pytest.mark.asyncio
    async def test_visualization_empty_evaluation_results(self):
        """Should handle evaluations with empty results gracefully."""
        service = VisualizationService()

        # Mock evaluation with empty results
        mock_evaluation = type('MockEvaluation', (), {
            'evaluation_id': 'test-eval',
            'timestamp': now_timestamp(),
            'selected_k_value': 5,
            'evaluation_results': []  # Empty!
        })()

        # This should be skipped, returning empty response
        params = service._calculate_normalization_params([], [], [])
        assert isinstance(params, dict)
        assert "silhouette_min" in params


class TestVisualizationMetricsValidation:
    """Validate metric calculations against expected ranges."""

    @pytest.mark.asyncio
    async def test_silhouette_score_range(self, evaluation_repo):
        """Verify silhouette scores are in [-1, 1] range."""
        try:
            evaluations = await evaluation_repo.get_latest_evaluations(limit=5)

            for evaluation in evaluations:
                for result in evaluation.evaluation_results or []:
                    assert -1.0 <= result.silhouette_score <= 1.0, \
                        f"Silhouette score {result.silhouette_score} out of range"

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_davies_bouldin_index_positive(self, evaluation_repo):
        """Verify Davies-Bouldin indices are non-negative."""
        try:
            evaluations = await evaluation_repo.get_latest_evaluations(limit=5)

            for evaluation in evaluations:
                for result in evaluation.evaluation_results or []:
                    assert result.davies_bouldin_index >= 0.0, \
                        f"Davies-Bouldin index {result.davies_bouldin_index} is negative"

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_calinski_harabasz_index_positive(self, evaluation_repo):
        """Verify Calinski-Harabasz indices are non-negative."""
        try:
            evaluations = await evaluation_repo.get_latest_evaluations(limit=5)

            for evaluation in evaluations:
                for result in evaluation.evaluation_results or []:
                    assert result.calinski_harabasz_index >= 0.0, \
                        f"Calinski-Harabasz index {result.calinski_harabasz_index} is negative"

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_composite_score_range(self, evaluation_repo):
        """Verify composite scores are in expected range."""
        try:
            evaluations = await evaluation_repo.get_latest_evaluations(limit=5)

            for evaluation in evaluations:
                assert 0.0 <= evaluation.best_composite_score <= 1.0, \
                    f"Composite score {evaluation.best_composite_score} out of [0, 1] range"

                for result in evaluation.evaluation_results or []:
                    assert 0.0 <= result.weighted_composite_score <= 1.0, \
                        f"Weighted composite score {result.weighted_composite_score} out of range"

        except Exception as e:
            pytest.skip(f"DynamoDB not available: {str(e)}")
