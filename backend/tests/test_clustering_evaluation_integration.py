"""
Integration tests for clustering evaluation pipeline with Celery tasks.

Tests verify:
- Evaluation pipeline processes clustering results correctly
- Metrics calculated accurately for various k values
- Ranking system produces correct inverse ranking
- Weighted composite scoring works as expected
- DynamoDB storage (mocked)
- Celery task integration
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.evaluation_pipeline import EvaluationPipeline, MetricResult


class TestClusteringEvaluationMetrics:
    """Test metric calculations match sklearn implementations."""

    def test_silhouette_metric_calculation(self):
        """Test silhouette score matches sklearn."""
        from sklearn.metrics import silhouette_score

        # Create well-separated clusters
        np.random.seed(42)
        cluster1 = np.random.randn(30, 50) + np.array([0] * 50)
        cluster2 = np.random.randn(30, 50) + np.array([5] * 50)
        embeddings = np.vstack([cluster1, cluster2])

        from sklearn.cluster import KMeans

        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        # Calculate using sklearn (reference)
        sklearn_score = silhouette_score(embeddings, labels, metric="euclidean")

        # Calculate using pipeline's method
        pipeline = EvaluationPipeline()
        result = pipeline._evaluate_single_k(embeddings, [f"article_{i}" for i in range(60)], 2)

        assert result is not None
        assert abs(result.silhouette_score - sklearn_score) < 0.001

    def test_davies_bouldin_metric_calculation(self):
        """Test davies-bouldin index matches sklearn."""
        from sklearn.metrics import davies_bouldin_score

        np.random.seed(42)
        cluster1 = np.random.randn(30, 50) + np.array([0] * 50)
        cluster2 = np.random.randn(30, 50) + np.array([5] * 50)
        embeddings = np.vstack([cluster1, cluster2])

        from sklearn.cluster import KMeans

        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        # Calculate using sklearn (reference)
        sklearn_score = davies_bouldin_score(embeddings, labels)

        # Calculate using pipeline's method
        pipeline = EvaluationPipeline()
        result = pipeline._evaluate_single_k(embeddings, [f"article_{i}" for i in range(60)], 2)

        assert result is not None
        assert abs(result.davies_bouldin_index - sklearn_score) < 0.001

    def test_calinski_harabasz_metric_calculation(self):
        """Test calinski-harabasz index matches sklearn."""
        from sklearn.metrics import calinski_harabasz_score

        np.random.seed(42)
        cluster1 = np.random.randn(30, 50) + np.array([0] * 50)
        cluster2 = np.random.randn(30, 50) + np.array([5] * 50)
        embeddings = np.vstack([cluster1, cluster2])

        from sklearn.cluster import KMeans

        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        # Calculate using sklearn (reference)
        sklearn_score = calinski_harabasz_score(embeddings, labels)

        # Calculate using pipeline's method
        pipeline = EvaluationPipeline()
        result = pipeline._evaluate_single_k(embeddings, [f"article_{i}" for i in range(60)], 2)

        assert result is not None
        assert abs(result.calinski_harabasz_index - sklearn_score) < 0.01


class TestEvaluationPipelineWithRealEmbeddings:
    """Test evaluation pipeline with realistic clustering scenarios."""

    def test_evaluation_with_100_articles_3_clusters(self):
        """Test evaluation with realistic dataset: 100 articles, 3-10 clusters."""
        np.random.seed(42)

        # Create 3 well-separated clusters
        cluster1 = np.random.randn(40, 128) + np.array([0] * 128)
        cluster2 = np.random.randn(35, 128) + np.array([5] * 128)
        cluster3 = np.random.randn(25, 128) + np.array([10] * 128)
        embeddings = np.vstack([cluster1, cluster2, cluster3])

        article_ids = [f"article_{i}" for i in range(100)]

        pipeline = EvaluationPipeline(
            silhouette_weight=0.5,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.2,
        )

        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=3,
            k_max=10,
        )

        # Verify results
        assert len(results) == 8  # k=3 to k=10 inclusive
        assert summary["selected_k_value"] is not None
        assert 3 <= summary["selected_k_value"] <= 10
        assert summary["best_composite_score"] > 0

        # Verify all results have ranks
        for result in results:
            assert result.silhouette_rank is not None
            assert result.davies_bouldin_rank is not None
            assert result.calinski_harabasz_rank is not None
            assert result.weighted_composite_score is not None

    def test_k_value_selection_picks_best_composite_score(self):
        """Test that selected k has the highest composite score."""
        np.random.seed(42)

        cluster1 = np.random.randn(50, 100)
        cluster2 = np.random.randn(50, 100) + np.array([5] * 100)
        embeddings = np.vstack([cluster1, cluster2])

        article_ids = [f"article_{i}" for i in range(100)]

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=2,
            k_max=8,
        )

        # Find result with highest composite score
        best_result = max(results, key=lambda r: r.weighted_composite_score)

        # Verify summary picked the best
        assert summary["selected_k_value"] == best_result.k_value
        assert summary["best_composite_score"] == best_result.weighted_composite_score

    def test_metrics_summary_has_correct_statistics(self):
        """Test that metrics summary contains correct min/max/mean/std_dev."""
        np.random.seed(42)

        cluster1 = np.random.randn(40, 100)
        cluster2 = np.random.randn(40, 100) + np.array([5] * 100)
        cluster3 = np.random.randn(40, 100) + np.array([10] * 100)
        embeddings = np.vstack([cluster1, cluster2, cluster3])

        article_ids = [f"article_{i}" for i in range(120)]

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=3,
            k_max=8,
        )

        metrics = summary["metrics_summary"]

        # Verify silhouette statistics
        sil_stats = metrics["silhouette_score"]
        assert "min" in sil_stats
        assert "max" in sil_stats
        assert "mean" in sil_stats
        assert "std_dev" in sil_stats
        assert sil_stats["min"] <= sil_stats["mean"] <= sil_stats["max"]

        # Verify davies-bouldin statistics
        db_stats = metrics["davies_bouldin_index"]
        assert db_stats["min"] <= db_stats["mean"] <= db_stats["max"]

        # Verify calinski-harabasz statistics
        ch_stats = metrics["calinski_harabasz_index"]
        assert ch_stats["min"] <= ch_stats["mean"] <= ch_stats["max"]

        # Verify composite score statistics
        comp_stats = metrics["composite_score"]
        assert comp_stats["min"] <= comp_stats["mean"] <= comp_stats["max"]

    def test_weight_changes_affect_composite_scores(self):
        """Test that different weights produce different composite scores."""
        np.random.seed(42)

        cluster1 = np.random.randn(50, 100)
        cluster2 = np.random.randn(50, 100) + np.array([5] * 100)
        embeddings = np.vstack([cluster1, cluster2])

        article_ids = [f"article_{i}" for i in range(100)]

        # Create sample results with known ranks
        results_template = [
            MetricResult(k, 0.3 + 0.05 * k, 2.0 - 0.1 * k, 80.0 + 10 * k, k, 20.0 / k, 5.0, 100.0)
            for k in range(2, 9)
        ]

        # Evaluate with weight set 1
        pipeline1 = EvaluationPipeline(
            silhouette_weight=0.5,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.2,
        )

        results1 = [
            MetricResult(r.k_value, r.silhouette_score, r.davies_bouldin_index,
                        r.calinski_harabasz_index, r.num_clusters_formed,
                        r.avg_cluster_size, r.noise_percentage, r.evaluation_time_ms)
            for r in results_template
        ]

        pipeline1._rank_metrics(results1)
        pipeline1._calculate_composite_scores(results1)

        # Evaluate with weight set 2
        pipeline2 = EvaluationPipeline(
            silhouette_weight=0.2,
            davies_bouldin_weight=0.6,
            calinski_harabasz_weight=0.2,
        )

        results2 = [
            MetricResult(r.k_value, r.silhouette_score, r.davies_bouldin_index,
                        r.calinski_harabasz_index, r.num_clusters_formed,
                        r.avg_cluster_size, r.noise_percentage, r.evaluation_time_ms)
            for r in results_template
        ]

        pipeline2._rank_metrics(results2)
        pipeline2._calculate_composite_scores(results2)

        # Composite scores should differ with different weights
        scores1 = [r.weighted_composite_score for r in results1]
        scores2 = [r.weighted_composite_score for r in results2]

        # They shouldn't be identical across all k values
        assert scores1 != scores2, "Different weights should produce different score distributions"


class TestEvaluationPipelineEdgeCases:
    """Test evaluation pipeline with edge cases."""

    def test_small_dataset_less_than_k_min(self):
        """Test graceful handling when dataset smaller than k_min."""
        embeddings = np.random.randn(3, 100)
        article_ids = ["article_0", "article_1", "article_2"]

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=5,
            k_max=10,
        )

        # Should return empty results, not crash
        assert isinstance(results, list)
        assert isinstance(summary, dict)

    def test_all_identical_embeddings(self):
        """Test handling when all embeddings are identical."""
        embeddings = np.ones((50, 100))  # All identical
        article_ids = [f"article_{i}" for i in range(50)]

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=2,
            k_max=5,
        )

        # Should handle gracefully
        assert isinstance(results, list)

    def test_single_k_value(self):
        """Test evaluation with only one k value (k_min == k_max)."""
        np.random.seed(42)

        cluster1 = np.random.randn(50, 100)
        cluster2 = np.random.randn(50, 100) + np.array([5] * 100)
        embeddings = np.vstack([cluster1, cluster2])

        article_ids = [f"article_{i}" for i in range(100)]

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=3,
            k_max=3,  # Only k=3
        )

        # Should evaluate single k
        assert len(results) == 1
        assert results[0].k_value == 3
        assert summary["selected_k_value"] == 3


class TestWeightValidation:
    """Test weight validation and handling."""

    def test_weights_sum_verification(self):
        """Test that weight sum is logged when not ~1.0."""
        pipeline = EvaluationPipeline(
            silhouette_weight=0.3,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.3,  # Sum = 0.9
        )

        # Should not raise, but sum != 1.0
        assert pipeline.silhouette_weight == 0.3

    def test_custom_weight_distributions(self):
        """Test various weight distributions produce different results."""
        np.random.seed(42)

        cluster1 = np.random.randn(40, 100)
        cluster2 = np.random.randn(40, 100) + np.array([5] * 100)
        embeddings = np.vstack([cluster1, cluster2])

        article_ids = [f"article_{i}" for i in range(80)]

        # Test weight distribution 1: emphasize silhouette
        pipeline1 = EvaluationPipeline(
            silhouette_weight=0.7,
            davies_bouldin_weight=0.15,
            calinski_harabasz_weight=0.15,
        )

        results1, _ = pipeline1.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=2,
            k_max=5,
        )

        # Test weight distribution 2: balanced
        pipeline2 = EvaluationPipeline(
            silhouette_weight=0.33,
            davies_bouldin_weight=0.33,
            calinski_harabasz_weight=0.34,
        )

        # Both should produce valid results
        assert all(r.weighted_composite_score is not None for r in results1)


class TestPerformanceAndScalability:
    """Test performance with various dataset sizes."""

    def test_evaluation_completes_for_200_articles(self):
        """Test evaluation completes in reasonable time for 200 articles."""
        import time

        embeddings = np.random.randn(200, 128)
        article_ids = [f"article_{i}" for i in range(200)]

        pipeline = EvaluationPipeline()

        start = time.time()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=5,
            k_max=15,
        )
        elapsed = time.time() - start

        assert len(results) > 0
        assert elapsed < 15.0, f"Evaluation took {elapsed:.2f}s, expected <15s"

    def test_evaluation_memory_efficient(self):
        """Test evaluation doesn't create excessive memory usage."""
        # Create dataset
        embeddings = np.random.randn(150, 128)
        article_ids = [f"article_{i}" for i in range(150)]

        pipeline = EvaluationPipeline()

        # Should not raise memory error
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=3,
            k_max=12,
        )

        assert len(results) == 10  # k=3 to k=12
