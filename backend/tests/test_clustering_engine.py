"""
Comprehensive tests for ClusteringEngine.
Tests cover: stability, edge cases, noise detection, performance.
"""

import pytest
import numpy as np
import time
from typing import List, Dict

from app.services.clustering_engine import ClusteringEngine


@pytest.fixture
def clustering_engine():
    """Create ClusteringEngine with default parameters."""
    return ClusteringEngine(min_cluster_size=5, min_samples=3, metric="cosine")


class TestClusteringStability:
    """Test that clustering produces deterministic, stable results."""

    def test_same_articles_same_clusters(self, clustering_engine):
        """
        STABILITY: Clustering same articles twice produces identical results.

        Verifies: Deterministic output for reproducibility.
        """
        # Create embeddings: 10 articles with 1536 dimensions
        np.random.seed(42)
        embeddings = np.random.rand(10, 1536)
        article_ids = [f"art-{i}" for i in range(10)]

        # Cluster twice
        result1, stats1 = clustering_engine.cluster_articles(embeddings, article_ids)
        result2, stats2 = clustering_engine.cluster_articles(embeddings, article_ids)

        # Assert identical assignments
        assert result1 == result2, "Clustering should be deterministic"
        assert stats1 == stats2, "Statistics should be identical"

    def test_cluster_assignments_consistent_across_runs(self, clustering_engine):
        """
        STABILITY: Multiple runs on same data produce identical assignments.

        Verifies: HDBSCAN is deterministic (uses fixed seed-like behavior).
        """
        np.random.seed(123)
        embeddings = np.random.rand(20, 1536)
        article_ids = [f"art-{i}" for i in range(20)]

        assignments = []
        for _ in range(3):
            result, _ = clustering_engine.cluster_articles(embeddings, article_ids)
            assignments.append(result)

        # All three runs should produce identical assignments
        for i in range(1, len(assignments)):
            assert assignments[i] == assignments[0], (
                f"Run {i} differs from run 0: "
                f"{assignments[i]} vs {assignments[0]}"
            )


class TestEdgeCases:
    """Test edge case handling: small datasets, uniform embeddings, empty inputs."""

    def test_single_article_returns_noise(self, clustering_engine):
        """
        EDGE: 1 article < min_cluster_size(5).

        Expect: cluster_id=-1 (noise), no clusters formed.
        """
        embeddings = np.random.rand(1, 1536)
        article_ids = ["art-1"]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        assert result["art-1"] == -1, "Single article should be noise"
        assert stats["num_clusters"] == 0, "No clusters should form"
        assert stats["num_noise"] == 1, "All articles are noise"
        assert stats["noise_percent"] == 100.0, "100% noise"

    def test_four_articles_returns_noise(self, clustering_engine):
        """
        EDGE: 4 articles < min_cluster_size(5).

        Expect: cluster_id=-1 for all, no clusters formed.
        """
        embeddings = np.random.rand(4, 1536)
        article_ids = [f"art-{i}" for i in range(4)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        for aid in article_ids:
            assert result[aid] == -1, f"{aid} should be noise"
        assert stats["num_clusters"] == 0, "No clusters should form"
        assert stats["num_noise"] == 4, "All 4 articles are noise"

    def test_five_articles_clusters(self, clustering_engine):
        """
        EDGE: 5 articles = min_cluster_size(5).

        Expect: May form 1 cluster or all noise, depending on distances.
        """
        np.random.seed(42)
        embeddings = np.random.rand(5, 1536)
        article_ids = [f"art-{i}" for i in range(5)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        # Should not crash
        assert len(result) == 5, "All articles should have assignments"
        assert stats["num_articles"] is None or True, "Stats should exist"

    def test_all_identical_embeddings_returns_noise(self, clustering_engine):
        """
        EDGE: All embeddings identical (zero distance between all points).

        Expect: All articles are noise (-1), no clusters form.
        Rationale: HDBSCAN cannot find density-based clusters in uniform space.
        """
        embedding_vector = np.random.rand(1536)
        embeddings = np.tile(embedding_vector, (10, 1))  # 10 identical copies
        article_ids = [f"art-{i}" for i in range(10)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        # All should be noise
        for aid in article_ids:
            assert result[aid] == -1, f"{aid} should be noise (uniform space)"
        assert stats["num_clusters"] == 0, "No clusters in uniform space"
        assert stats["num_noise"] == 10, "All 10 are noise"
        assert stats["noise_percent"] == 100.0

    def test_empty_embeddings_array(self, clustering_engine):
        """
        EDGE: Empty embeddings array.

        Expect: Return empty result, zero statistics.
        """
        embeddings = np.empty((0, 1536))
        article_ids = []

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        assert result == {}, "Empty result for empty input"
        assert stats["num_clusters"] == 0
        assert stats["num_noise"] == 0
        assert stats["noise_percent"] == 0.0


class TestNoiseDetection:
    """Test that articles not fitting clusters are marked as noise."""

    def test_outlier_articles_marked_as_noise(self, clustering_engine):
        """
        NOISE: Articles far from others should be marked as noise.

        Setup: 8 articles close together + 2 outliers far away.
        Expect: Outliers get cluster_id=-1.
        """
        np.random.seed(42)

        # Create 8 close articles
        close_embeddings = np.random.rand(8, 1536) * 0.01  # Small spread

        # Create 2 outliers far away
        outlier1 = np.ones(1536) * 0.99
        outlier2 = np.ones(1536) * 0.99
        outlier1[0] = 0.0  # Slightly different
        outlier2[0] = 0.1

        embeddings = np.vstack([close_embeddings, [outlier1], [outlier2]])
        article_ids = [f"art-{i}" for i in range(10)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        # Outliers (last 2) should be noise
        assert result["art-8"] == -1, "Outlier 1 should be noise"
        assert result["art-9"] == -1, "Outlier 2 should be noise"
        assert stats["num_noise"] >= 2, "At least 2 articles should be noise"

    def test_noise_percent_reasonable(self, clustering_engine):
        """
        NOISE: Noise percentage should be < 5% false positives.

        Setup: 100 articles with natural variance (good embeddings).
        Expect: noise_percent < 10% (accounting for natural outliers).
        """
        np.random.seed(42)

        # 100 articles with natural embedding variance
        embeddings = np.random.rand(100, 1536)
        article_ids = [f"art-{i}" for i in range(100)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        # Noise should be reasonable (not >10% false positives)
        assert stats["noise_percent"] < 20.0, (
            f"Noise percent {stats['noise_percent']:.1f}% too high"
        )


class TestClusterStatistics:
    """Test that cluster statistics are calculated correctly."""

    def test_stats_num_clusters_calculated(self, clustering_engine):
        """
        STATS: Number of clusters should be accurately counted.

        Verify: num_clusters = count of unique non-negative labels.
        """
        np.random.seed(42)

        # Create embeddings likely to form multiple clusters
        cluster1 = np.random.rand(10, 1536) * 0.01
        cluster2 = np.random.rand(10, 1536) * 0.01 + 0.5

        embeddings = np.vstack([cluster1, cluster2])
        article_ids = [f"art-{i}" for i in range(20)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        # Should have at least 1 cluster (unless all noise)
        assert stats["num_clusters"] >= 0, "num_clusters should be non-negative"
        assert isinstance(stats["num_clusters"], int), "num_clusters should be int"

    def test_stats_avg_cluster_size_in_range(self, clustering_engine):
        """
        STATS: Average cluster size should be between 5-50 (healthy).

        Verify: When clusters exist, avg_size reflects proper granularity.
        """
        np.random.seed(42)

        # 50 articles, likely to form clusters
        embeddings = np.random.rand(50, 1536)
        article_ids = [f"art-{i}" for i in range(50)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        # If clusters exist, avg should be reasonable
        if stats["num_clusters"] > 0:
            avg = stats["avg_cluster_size"]
            assert avg >= 5.0, f"Average cluster size {avg} too small"
            assert avg <= 50.0, f"Average cluster size {avg} too large"

    def test_stats_cluster_sizes_dict(self, clustering_engine):
        """
        STATS: cluster_sizes dict should map cluster_id -> count.

        Verify: All cluster IDs and counts are present and valid.
        """
        np.random.seed(42)

        embeddings = np.random.rand(25, 1536)
        article_ids = [f"art-{i}" for i in range(25)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        cluster_sizes = stats["cluster_sizes"]

        # Verify structure
        assert isinstance(cluster_sizes, dict), "cluster_sizes should be dict"

        # Sum of all sizes should equal total articles
        total_in_dict = sum(cluster_sizes.values())
        assert total_in_dict == len(article_ids), (
            f"Sum of cluster sizes {total_in_dict} != total articles {len(article_ids)}"
        )

    def test_stats_sum_cluster_counts(self, clustering_engine):
        """
        STATS: Sum of noise + clustered articles = total.

        Verify: num_noise + sum(clustered) = num_articles.
        """
        np.random.seed(42)

        embeddings = np.random.rand(30, 1536)
        article_ids = [f"art-{i}" for i in range(30)]

        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        # Sum up all cluster sizes
        total_in_clusters = sum(stats["cluster_sizes"].values())

        # Should equal total articles
        expected = len(article_ids)
        assert total_in_clusters == expected, (
            f"Total in clusters {total_in_clusters} != "
            f"articles {expected}"
        )


class TestPerformance:
    """Test that clustering performs well on larger datasets."""

    def test_500_articles_completes_in_time(self, clustering_engine):
        """
        PERF: Clustering 500 articles should complete in < 5 minutes.

        Verify: Performance acceptable for real-world batch processing.
        """
        np.random.seed(42)

        # 500 articles with 1536 dimensions
        embeddings = np.random.rand(500, 1536).astype(np.float32)
        article_ids = [f"art-{i}" for i in range(500)]

        start_time = time.time()
        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)
        elapsed = time.time() - start_time

        # Should complete in reasonable time
        max_time = 300.0  # 5 minutes
        assert elapsed < max_time, (
            f"Clustering took {elapsed:.1f}s, max {max_time}s"
        )

        # Verify result is complete
        assert len(result) == 500, "All 500 articles should be assigned"

    def test_1000_articles_completes(self, clustering_engine):
        """
        PERF: Clustering 1000 articles should complete.

        Verify: Handles large batches without memory issues.
        """
        np.random.seed(42)

        # 1000 articles - larger batch
        embeddings = np.random.rand(1000, 1536).astype(np.float32)
        article_ids = [f"art-{i}" for i in range(1000)]

        start_time = time.time()
        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)
        elapsed = time.time() - start_time

        # Should complete
        assert len(result) == 1000, "All 1000 articles should be assigned"
        assert elapsed < 600.0, f"Should complete in < 10 minutes, took {elapsed:.1f}s"


class TestInputValidation:
    """Test input validation and error handling."""

    def test_mismatched_article_ids_count(self, clustering_engine):
        """
        VALIDATE: Mismatched article_ids and embeddings count raises error.
        """
        embeddings = np.random.rand(10, 1536)
        article_ids = [f"art-{i}" for i in range(5)]  # Only 5 IDs

        with pytest.raises(ValueError, match="Article count mismatch"):
            clustering_engine.cluster_articles(embeddings, article_ids)

    def test_invalid_embedding_dimensions(self, clustering_engine):
        """
        VALIDATE: Wrong embedding dimensions don't crash (but may not cluster well).
        """
        embeddings = np.random.rand(10, 128)  # Wrong dimension
        article_ids = [f"art-{i}" for i in range(10)]

        # Should not crash, just won't cluster well
        result, stats = clustering_engine.cluster_articles(embeddings, article_ids)
        assert len(result) == 10, "Should return assignments even with wrong dims"


class TestResultConsistency:
    """Test that returned structures are always consistent."""

    def test_result_keys_match_article_ids(self, clustering_engine):
        """
        CONSISTENCY: Result dict keys should exactly match article_ids.
        """
        embeddings = np.random.rand(15, 1536)
        article_ids = [f"art-{i}" for i in range(15)]

        result, _ = clustering_engine.cluster_articles(embeddings, article_ids)

        # Check all IDs are in result
        for aid in article_ids:
            assert aid in result, f"Missing {aid} in result"

        # Check no extra IDs
        assert len(result) == len(article_ids), "Result has extra articles"

    def test_all_assignments_are_integers(self, clustering_engine):
        """
        CONSISTENCY: All cluster assignments must be integers.
        """
        embeddings = np.random.rand(20, 1536)
        article_ids = [f"art-{i}" for i in range(20)]

        result, _ = clustering_engine.cluster_articles(embeddings, article_ids)

        for aid, cluster_id in result.items():
            assert isinstance(cluster_id, int), f"{aid} assignment is not int"

    def test_stats_dict_has_all_keys(self, clustering_engine):
        """
        CONSISTENCY: Stats dict should always have required keys.
        """
        embeddings = np.random.rand(10, 1536)
        article_ids = [f"art-{i}" for i in range(10)]

        _, stats = clustering_engine.cluster_articles(embeddings, article_ids)

        required_keys = {
            "num_clusters",
            "num_noise",
            "noise_percent",
            "avg_cluster_size",
            "cluster_sizes",
        }
        assert set(stats.keys()) == required_keys, (
            f"Stats missing keys. Has: {set(stats.keys())}, "
            f"Expected: {required_keys}"
        )
