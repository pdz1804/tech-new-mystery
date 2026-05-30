"""
Comprehensive tests for clustering evaluation pipeline.

Tests cover:
- Metric calculation: Silhouette, Davies-Bouldin, Calinski-Harabasz
- Ranking system: inverse ranking (rank 1 = best)
- Composite scoring: weighted calculation
- K-value selection: best composite score selection
- Summary statistics: min, max, mean, std_dev
- Edge cases: small datasets, single cluster, all noise
- Integration: full pipeline with real embeddings
"""

import pytest
import numpy as np
from app.services.evaluation_pipeline import EvaluationPipeline, MetricResult


class TestMetricResult:
    """Test MetricResult dataclass."""

    def test_metric_result_creation(self):
        """Test creating MetricResult with all fields."""
        result = MetricResult(
            k_value=5,
            silhouette_score=0.5,
            davies_bouldin_index=1.5,
            calinski_harabasz_index=100.0,
            num_clusters_formed=5,
            avg_cluster_size=20.0,
            noise_percentage=5.0,
            evaluation_time_ms=100.0,
        )

        assert result.k_value == 5
        assert result.silhouette_score == 0.5
        assert result.davies_bouldin_index == 1.5
        assert result.calinski_harabasz_index == 100.0

    def test_metric_result_to_dict(self):
        """Test converting MetricResult to dictionary."""
        result = MetricResult(
            k_value=5,
            silhouette_score=0.5,
            davies_bouldin_index=1.5,
            calinski_harabasz_index=100.0,
            num_clusters_formed=5,
            avg_cluster_size=20.0,
            noise_percentage=5.0,
            evaluation_time_ms=100.0,
            silhouette_rank=1,
            davies_bouldin_rank=2,
            calinski_harabasz_rank=3,
            weighted_composite_score=0.5,
        )

        result_dict = result.to_dict()

        assert result_dict["k_value"] == 5
        assert result_dict["silhouette_score"] == 0.5
        assert result_dict["silhouette_rank"] == 1
        assert result_dict["weighted_composite_score"] == 0.5


class TestEvaluationPipelineInitialization:
    """Test EvaluationPipeline initialization."""

    def test_default_weights(self):
        """Test initialization with default weights."""
        pipeline = EvaluationPipeline()

        assert pipeline.silhouette_weight == 0.5
        assert pipeline.davies_bouldin_weight == 0.3
        assert pipeline.calinski_harabasz_weight == 0.2

    def test_custom_weights(self):
        """Test initialization with custom weights."""
        pipeline = EvaluationPipeline(
            silhouette_weight=0.6,
            davies_bouldin_weight=0.2,
            calinski_harabasz_weight=0.2,
        )

        assert pipeline.silhouette_weight == 0.6
        assert pipeline.davies_bouldin_weight == 0.2
        assert pipeline.calinski_harabasz_weight == 0.2

    def test_zero_weights_raises_error(self):
        """Test that zero sum of weights raises error."""
        with pytest.raises(ValueError, match="Sum of weights must be positive"):
            EvaluationPipeline(
                silhouette_weight=0.0,
                davies_bouldin_weight=0.0,
                calinski_harabasz_weight=0.0,
            )


class TestRankingSystem:
    """Test metric ranking logic."""

    def test_silhouette_ranking_descending(self):
        """Test silhouette score ranking (higher is better)."""
        pipeline = EvaluationPipeline()

        results = [
            MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
            MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0),
            MetricResult(7, 0.4, 1.8, 90.0, 7, 14.0, 5.0, 120.0),
        ]

        pipeline._rank_metrics(results)

        # 0.5 should be rank 1 (best), 0.4 rank 2, 0.3 rank 3
        assert results[1].silhouette_rank == 1  # 0.5
        assert results[2].silhouette_rank == 2  # 0.4
        assert results[0].silhouette_rank == 3  # 0.3

    def test_davies_bouldin_ranking_ascending(self):
        """Test davies-bouldin index ranking (lower is better)."""
        pipeline = EvaluationPipeline()

        results = [
            MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
            MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0),
            MetricResult(7, 0.4, 1.8, 90.0, 7, 14.0, 5.0, 120.0),
        ]

        pipeline._rank_metrics(results)

        # 1.5 should be rank 1 (best), 1.8 rank 2, 2.0 rank 3
        assert results[1].davies_bouldin_rank == 1  # 1.5
        assert results[2].davies_bouldin_rank == 2  # 1.8
        assert results[0].davies_bouldin_rank == 3  # 2.0

    def test_calinski_harabasz_ranking_descending(self):
        """Test calinski-harabasz index ranking (higher is better)."""
        pipeline = EvaluationPipeline()

        results = [
            MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
            MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0),
            MetricResult(7, 0.4, 1.8, 90.0, 7, 14.0, 5.0, 120.0),
        ]

        pipeline._rank_metrics(results)

        # 100.0 should be rank 1 (best), 90.0 rank 2, 80.0 rank 3
        assert results[1].calinski_harabasz_rank == 1  # 100.0
        assert results[2].calinski_harabasz_rank == 2  # 90.0
        assert results[0].calinski_harabasz_rank == 3  # 80.0


class TestCompositeScoring:
    """Test weighted composite score calculation."""

    def test_composite_score_formula(self):
        """Test that composite score = sum(weight / rank)."""
        pipeline = EvaluationPipeline(
            silhouette_weight=0.5,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.2,
        )

        results = [
            MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
        ]

        # Manually set ranks
        results[0].silhouette_rank = 5
        results[0].davies_bouldin_rank = 2
        results[0].calinski_harabasz_rank = 8

        pipeline._calculate_composite_scores(results)

        # Expected: 0.5/5 + 0.3/2 + 0.2/8 = 0.1 + 0.15 + 0.025 = 0.275
        assert abs(results[0].weighted_composite_score - 0.275) < 0.001

    def test_best_rank_contributes_most(self):
        """Test that rank 1 (best) contributes more than rank 2."""
        pipeline = EvaluationPipeline(
            silhouette_weight=0.5,
            davies_bouldin_weight=0.3,
            calinski_harabasz_weight=0.2,
        )

        result1 = MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0)
        result1.silhouette_rank = 1
        result1.davies_bouldin_rank = 5
        result1.calinski_harabasz_rank = 5

        result2 = MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0)
        result2.silhouette_rank = 2
        result2.davies_bouldin_rank = 5
        result2.calinski_harabasz_rank = 5

        pipeline._calculate_composite_scores([result1, result2])

        # result1 has rank 1 for silhouette, so should score higher
        assert result1.weighted_composite_score > result2.weighted_composite_score

    def test_balanced_weights(self):
        """Test with balanced weights across all metrics."""
        pipeline = EvaluationPipeline(
            silhouette_weight=0.33,
            davies_bouldin_weight=0.33,
            calinski_harabasz_weight=0.34,
        )

        results = [
            MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
            MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0),
        ]

        pipeline._rank_metrics(results)
        pipeline._calculate_composite_scores(results)

        # Both should have composite scores
        assert all(r.weighted_composite_score is not None for r in results)
        assert all(r.weighted_composite_score > 0 for r in results)


class TestSummaryGeneration:
    """Test summary statistics generation."""

    def test_summary_contains_required_fields(self):
        """Test that summary has all required fields."""
        pipeline = EvaluationPipeline()

        results = [
            MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
            MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0),
        ]

        results[0].silhouette_rank = 2
        results[0].davies_bouldin_rank = 2
        results[0].calinski_harabasz_rank = 2
        results[0].weighted_composite_score = 0.3

        results[1].silhouette_rank = 1
        results[1].davies_bouldin_rank = 1
        results[1].calinski_harabasz_rank = 1
        results[1].weighted_composite_score = 0.5

        best = max(results, key=lambda r: r.weighted_composite_score)
        summary = pipeline._generate_summary(results, best)

        assert "selected_k_value" in summary
        assert "best_composite_score" in summary
        assert "evaluation_results" in summary
        assert "metrics_summary" in summary

    def test_summary_selects_correct_k_value(self):
        """Test that summary selects k with highest composite score."""
        pipeline = EvaluationPipeline()

        results = [
            MetricResult(5, 0.3, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
            MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0),
            MetricResult(7, 0.4, 1.8, 90.0, 7, 14.0, 5.0, 120.0),
        ]

        # Assign composite scores
        results[0].weighted_composite_score = 0.2
        results[1].weighted_composite_score = 0.5  # Best
        results[2].weighted_composite_score = 0.3

        best = max(results, key=lambda r: r.weighted_composite_score)
        summary = pipeline._generate_summary(results, best)

        assert summary["selected_k_value"] == 6
        assert summary["best_composite_score"] == 0.5

    def test_metrics_summary_statistics(self):
        """Test that metrics summary contains correct statistics."""
        pipeline = EvaluationPipeline()

        results = [
            MetricResult(5, 0.2, 2.0, 80.0, 5, 20.0, 5.0, 100.0),
            MetricResult(6, 0.5, 1.5, 100.0, 6, 17.0, 4.0, 110.0),
            MetricResult(7, 0.4, 1.8, 90.0, 7, 14.0, 5.0, 120.0),
        ]

        results[0].weighted_composite_score = 0.2
        results[1].weighted_composite_score = 0.5
        results[2].weighted_composite_score = 0.3

        best = max(results, key=lambda r: r.weighted_composite_score)
        summary = pipeline._generate_summary(results, best)

        metrics = summary["metrics_summary"]

        # Check silhouette statistics
        assert metrics["silhouette_score"]["min"] == 0.2
        assert metrics["silhouette_score"]["max"] == 0.5
        assert metrics["silhouette_score"]["mean"] > 0.2
        assert "std_dev" in metrics["silhouette_score"]

        # Check all metrics present
        assert "davies_bouldin_index" in metrics
        assert "calinski_harabasz_index" in metrics
        assert "composite_score" in metrics


class TestEvaluationPipelineIntegration:
    """Integration tests for full evaluation pipeline."""

    def test_simple_two_cluster_evaluation(self):
        """Test evaluation with simple two well-separated clusters."""
        # Create embeddings: two well-separated clusters
        cluster1 = np.random.randn(50, 100) + np.array([0] * 100)
        cluster2 = np.random.randn(50, 100) + np.array([5] * 100)
        embeddings = np.vstack([cluster1, cluster2])

        # Create article IDs
        article_ids = [f"article_{i}" for i in range(100)]

        # Create empty cluster assignments (not used in k-means evaluation)
        cluster_assignments = {}

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments=cluster_assignments,
            article_ids=article_ids,
            k_min=2,
            k_max=5,
        )

        # Should evaluate k=2,3,4,5
        assert len(results) > 0, "Should generate evaluation results"
        assert summary["selected_k_value"] is not None
        assert summary["best_composite_score"] > 0

    def test_evaluation_with_large_dataset(self):
        """Test evaluation with 200+ articles."""
        np.random.seed(42)

        # Create 3 well-separated clusters with 100+ articles
        cluster1 = np.random.randn(100, 128) + np.array([0] * 128)
        cluster2 = np.random.randn(80, 128) + np.array([5] * 128)
        cluster3 = np.random.randn(70, 128) + np.array([10] * 128)
        embeddings = np.vstack([cluster1, cluster2, cluster3])

        article_ids = [f"article_{i}" for i in range(250)]
        cluster_assignments = {}

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments=cluster_assignments,
            article_ids=article_ids,
            k_min=3,
            k_max=10,
        )

        assert len(results) > 0
        assert summary["selected_k_value"] in [3, 4, 5, 6, 7, 8, 9, 10]

    def test_evaluation_with_1536_dim_embeddings(self):
        """Test evaluation with real OpenAI embedding dimensions (1536)."""
        np.random.seed(42)

        # Create clusters with 1536 dimensions (OpenAI size)
        cluster1 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster1 /= np.linalg.norm(cluster1, axis=1, keepdims=True)

        cluster2 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster2 /= np.linalg.norm(cluster2, axis=1, keepdims=True)
        cluster2 += np.array([0.3] * 1536)

        embeddings = np.vstack([cluster1, cluster2])
        article_ids = [f"article_{i}" for i in range(100)]
        cluster_assignments = {}

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments=cluster_assignments,
            article_ids=article_ids,
            k_min=2,
            k_max=5,
        )

        assert len(results) > 0
        assert summary["selected_k_value"] is not None

    def test_ranking_produces_valid_ranks(self):
        """Test that ranking produces valid rank numbers."""
        cluster1 = np.random.randn(50, 100)
        cluster2 = np.random.randn(50, 100) + np.array([5] * 100)
        embeddings = np.vstack([cluster1, cluster2])

        article_ids = [f"article_{i}" for i in range(100)]
        cluster_assignments = {}

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments=cluster_assignments,
            article_ids=article_ids,
            k_min=2,
            k_max=5,
        )

        # Verify all results have ranks in valid range
        for result in results:
            assert 1 <= result.silhouette_rank <= len(results)
            assert 1 <= result.davies_bouldin_rank <= len(results)
            assert 1 <= result.calinski_harabasz_rank <= len(results)

    def test_composite_scores_all_positive(self):
        """Test that all composite scores are positive."""
        cluster1 = np.random.randn(50, 100)
        cluster2 = np.random.randn(50, 100) + np.array([5] * 100)
        embeddings = np.vstack([cluster1, cluster2])

        article_ids = [f"article_{i}" for i in range(100)]
        cluster_assignments = {}

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments=cluster_assignments,
            article_ids=article_ids,
            k_min=2,
            k_max=5,
        )

        # All composite scores should be positive
        for result in results:
            assert result.weighted_composite_score > 0, f"Negative score for k={result.k_value}"

    def test_edge_case_less_articles_than_k_min(self):
        """Test handling when dataset has fewer articles than k_min."""
        embeddings = np.random.randn(3, 100)  # Only 3 articles
        article_ids = ["article_0", "article_1", "article_2"]
        cluster_assignments = {}

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments=cluster_assignments,
            article_ids=article_ids,
            k_min=5,
            k_max=10,
        )

        # Should gracefully handle small dataset
        assert isinstance(results, list)
        assert isinstance(summary, dict)

    def test_three_articles_clamps_to_valid_k_range(self):
        """Test that 3 embeddings can still evaluate with k=2."""
        embeddings = np.array(
            [
                [0.0, 0.0],
                [0.1, 0.1],
                [5.0, 5.0],
            ]
        )
        article_ids = ["article_0", "article_1", "article_2"]

        pipeline = EvaluationPipeline()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments={},
            article_ids=article_ids,
            k_min=5,
            k_max=10,
        )

        assert len(results) == 1
        assert results[0].k_value == 2
        assert summary["selected_k_value"] == 2

    def test_performance_completes_in_reasonable_time(self):
        """Test that evaluation completes in reasonable time."""
        import time

        # Create 150-article dataset
        embeddings = np.random.randn(150, 128)
        article_ids = [f"article_{i}" for i in range(150)]
        cluster_assignments = {}

        pipeline = EvaluationPipeline()

        start = time.time()
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings,
            cluster_assignments=cluster_assignments,
            article_ids=article_ids,
            k_min=5,
            k_max=15,
        )
        elapsed = time.time() - start

        # Should complete in under 10 seconds for 150 articles and k range of 5-15
        assert elapsed < 10.0, f"Evaluation took {elapsed:.2f}s, expected <10s"
        assert len(results) > 0
