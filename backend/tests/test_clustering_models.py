"""Unit tests for clustering evaluation PynamoDB models."""

import pytest
import time
from moto import mock_aws

from app.models.clustering import (
    ClusteringEvaluationModel,
    ClusteringParamsModel,
    EvaluationResultItem,
)


@mock_aws
class TestClusteringEvaluationModel:
    """Tests for ClusteringEvaluationModel."""

    def test_evaluation_model_creation(self):
        """Test creating and saving an evaluation result."""
        # Create table
        ClusteringEvaluationModel.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True,
        )

        # Create evaluation result item
        now = int(time.time())
        eval_result = EvaluationResultItem(
            k_value=5,
            silhouette_score=0.42,
            davies_bouldin_index=1.8,
            calinski_harabasz_index=285.3,
            silhouette_rank=25,
            davies_bouldin_rank=8,
            calinski_harabasz_rank=42,
            weighted_composite_score=0.285,
            num_clusters_formed=5,
            avg_cluster_size=18.4,
            noise_percentage=3.2,
            evaluation_time_ms=234,
        )

        # Create evaluation model
        evaluation = ClusteringEvaluationModel(
            evaluation_id="eval-2026-05-28-18-00",
            run_timestamp=now,
            evaluation_type="scheduled",
            total_articles_evaluated=500,
            evaluation_results=[eval_result],
            selected_k_value=6,
            best_composite_score=0.542,
            admin_weights={
                "silhouette_weight": 0.5,
                "davies_bouldin_weight": 0.3,
                "calinski_harabasz_weight": 0.2,
            },
            quality_threshold_met=True,
            metrics_summary={
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
            },
            completed_at=now + 300,
            ttl=now + 2592000,  # 30 days
        )

        # Save to DynamoDB
        evaluation.save()

        # Retrieve and verify
        retrieved = ClusteringEvaluationModel.get(
            "eval-2026-05-28-18-00",
        )
        assert retrieved.evaluation_id == "eval-2026-05-28-18-00"
        assert retrieved.evaluation_type == "scheduled"
        assert retrieved.total_articles_evaluated == 500
        assert retrieved.selected_k_value == 6
        assert retrieved.best_composite_score == 0.542
        assert retrieved.quality_threshold_met is True
        assert len(retrieved.evaluation_results) == 1
        assert retrieved.evaluation_results[0].k_value == 5
        assert retrieved.evaluation_results[0].silhouette_score == 0.42

    def test_evaluation_model_attributes(self):
        """Test evaluation model has correct attributes."""
        # Create table
        ClusteringEvaluationModel.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True,
        )

        now = int(time.time())
        evaluation = ClusteringEvaluationModel(
            evaluation_id="eval-2026-05-28-19-00",
            run_timestamp=now,
            evaluation_type="manual",
            total_articles_evaluated=600,
            evaluation_results=[],
            selected_k_value=10,
            best_composite_score=0.65,
            admin_weights={
                "silhouette_weight": 0.6,
                "davies_bouldin_weight": 0.2,
                "calinski_harabasz_weight": 0.2,
            },
            quality_threshold_met=True,
            metrics_summary={},
            completed_at=now + 400,
            ttl=now + 2592000,
        )

        evaluation.save()

        # Verify all attributes are accessible
        retrieved = ClusteringEvaluationModel.get("eval-2026-05-28-19-00")
        assert retrieved.run_timestamp == now
        assert retrieved.evaluation_type == "manual"
        assert retrieved.total_articles_evaluated == 600
        assert retrieved.selected_k_value == 10
        assert retrieved.admin_weights["silhouette_weight"] == 0.6
        assert retrieved.ttl == now + 2592000


@mock_aws
class TestClusteringParamsModel:
    """Tests for ClusteringParamsModel."""

    def test_params_model_creation(self):
        """Test creating and saving clustering parameters."""
        # Create table
        ClusteringParamsModel.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True,
        )

        now = int(time.time())

        # Create params model
        params = ClusteringParamsModel(
            param_id="default",
            silhouette_weight=0.5,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.2,
            min_cluster_size=5,
            min_samples=3,
            quality_threshold=0.6,
            last_updated=now,
        )

        # Save to DynamoDB
        params.save()

        # Retrieve and verify
        retrieved = ClusteringParamsModel.get("default")
        assert retrieved.param_id == "default"
        assert retrieved.silhouette_weight == 0.5
        assert retrieved.davies_bouldin_weight == 0.3
        assert retrieved.calinski_harabasz_weight == 0.2
        assert retrieved.min_cluster_size == 5
        assert retrieved.min_samples == 3
        assert retrieved.quality_threshold == 0.6
        assert retrieved.last_updated == now

    def test_params_model_weight_update(self):
        """Test updating clustering parameter weights."""
        # Create table
        ClusteringParamsModel.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True,
        )

        now = int(time.time())

        # Create initial params
        params = ClusteringParamsModel(
            param_id="default",
            silhouette_weight=0.5,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.2,
            min_cluster_size=5,
            min_samples=3,
            quality_threshold=0.6,
            last_updated=now,
        )
        params.save()

        # Update weights
        updated_time = now + 3600
        params.silhouette_weight = 0.6
        params.davies_bouldin_weight = 0.2
        params.calinski_harabasz_weight = 0.2
        params.last_updated = updated_time
        params.save()

        # Retrieve and verify update
        retrieved = ClusteringParamsModel.get("default")
        assert retrieved.silhouette_weight == 0.6
        assert retrieved.davies_bouldin_weight == 0.2
        assert retrieved.calinski_harabasz_weight == 0.2
        assert retrieved.last_updated == updated_time

    def test_params_model_threshold_update(self):
        """Test updating quality threshold."""
        # Create table
        ClusteringParamsModel.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True,
        )

        now = int(time.time())

        # Create params with default threshold
        params = ClusteringParamsModel(
            param_id="default",
            silhouette_weight=0.5,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.2,
            min_cluster_size=5,
            min_samples=3,
            quality_threshold=0.6,
            last_updated=now,
        )
        params.save()

        # Update threshold
        params.quality_threshold = 0.75
        params.last_updated = now + 7200
        params.save()

        # Verify
        retrieved = ClusteringParamsModel.get("default")
        assert retrieved.quality_threshold == 0.75


@mock_aws
class TestEvaluationResultItem:
    """Tests for EvaluationResultItem MapAttribute."""

    def test_evaluation_result_item_in_list(self):
        """Test EvaluationResultItem within evaluation results list."""
        ClusteringEvaluationModel.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True,
        )

        now = int(time.time())

        # Create multiple result items
        results = [
            EvaluationResultItem(
                k_value=5,
                silhouette_score=0.42,
                davies_bouldin_index=1.8,
                calinski_harabasz_index=285.3,
                silhouette_rank=5,
                davies_bouldin_rank=3,
                calinski_harabasz_rank=8,
                weighted_composite_score=0.285,
                num_clusters_formed=5,
                avg_cluster_size=18.4,
                noise_percentage=3.2,
                evaluation_time_ms=234,
            ),
            EvaluationResultItem(
                k_value=6,
                silhouette_score=0.51,
                davies_bouldin_index=1.6,
                calinski_harabasz_index=312.8,
                silhouette_rank=1,
                davies_bouldin_rank=1,
                calinski_harabasz_rank=2,
                weighted_composite_score=0.542,
                num_clusters_formed=6,
                avg_cluster_size=16.8,
                noise_percentage=2.1,
                evaluation_time_ms=241,
            ),
        ]

        # Create evaluation with multiple results
        evaluation = ClusteringEvaluationModel(
            evaluation_id="eval-2026-05-28-multi",
            run_timestamp=now,
            evaluation_type="scheduled",
            total_articles_evaluated=500,
            evaluation_results=results,
            selected_k_value=6,
            best_composite_score=0.542,
            admin_weights={
                "silhouette_weight": 0.5,
                "davies_bouldin_weight": 0.3,
                "calinski_harabasz_weight": 0.2,
            },
            quality_threshold_met=True,
            metrics_summary={},
            completed_at=now + 300,
            ttl=now + 2592000,
        )

        evaluation.save()

        # Retrieve and verify
        retrieved = ClusteringEvaluationModel.get("eval-2026-05-28-multi")
        assert len(retrieved.evaluation_results) == 2
        assert retrieved.evaluation_results[0].k_value == 5
        assert retrieved.evaluation_results[0].silhouette_score == 0.42
        assert retrieved.evaluation_results[1].k_value == 6
        assert retrieved.evaluation_results[1].silhouette_score == 0.51
        assert retrieved.evaluation_results[1].weighted_composite_score == 0.542
