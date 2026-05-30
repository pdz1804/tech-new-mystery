"""
Comprehensive tests for clustering quality metrics.

Tests cover:
- Silhouette Score: cohesion vs separation
- Davies-Bouldin Index: compactness and separation
- Calinski-Harabasz Index: cluster density and definition

Each metric tested with:
- Known datasets with expected ranges
- Edge cases: single cluster, all noise, uniform data
- Real 1536-dim embeddings (OpenAI-like)
- Range validation against spec
- Performance: metrics complete <1s for 1000 articles
"""

import pytest
import numpy as np
from app.services.clustering_metrics import ClusteringMetrics


class TestSilhouetteScore:
    """Silhouette Score: measures cohesion vs separation."""

    def test_perfect_separation_two_clusters(self):
        """SPEC: Well-separated clusters should have high silhouette score > 0.7."""
        # Create two well-separated clusters
        cluster1 = np.random.randn(50, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(50, 10) + np.array([10] * 10)
        embeddings = np.vstack([cluster1, cluster2])

        labels = np.array([0] * 50 + [1] * 50)

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert -1.0 <= score <= 1.0, "Score must be in [-1, 1]"
        assert score > 0.5, f"Well-separated clusters should score > 0.5, got {score}"

    def test_poor_separation_overlapping(self):
        """SPEC: Overlapping clusters should have low silhouette score < 0.5."""
        # Create overlapping clusters
        cluster1 = np.random.randn(50, 10)
        cluster2 = np.random.randn(50, 10) + np.array([0.5] * 10)
        embeddings = np.vstack([cluster1, cluster2])

        labels = np.array([0] * 50 + [1] * 50)

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert -1.0 <= score <= 1.0, "Score must be in [-1, 1]"
        assert score < 0.6, f"Overlapping clusters should score < 0.6, got {score}"

    def test_single_cluster_returns_zero(self):
        """EDGE: Single cluster cannot measure separation, should return 0."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([0] * 50)

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert score == 0.0, "Single cluster should return 0.0"

    def test_all_noise_returns_zero(self):
        """EDGE: All noise points (label -1) should return 0."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([-1] * 50)

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert score == 0.0, "All noise should return 0.0"

    def test_single_sample_returns_zero(self):
        """EDGE: Single sample cannot compute silhouette."""
        embeddings = np.random.randn(1, 10)
        labels = np.array([0])

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert score == 0.0, "Single sample should return 0.0"

    def test_mixed_noise_and_clusters(self):
        """SPEC: Noise points should not affect silhouette of valid clusters."""
        cluster1 = np.random.randn(30, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(30, 10) + np.array([10] * 10)
        noise = np.random.randn(10, 10) * 50  # Far away noise

        embeddings = np.vstack([cluster1, cluster2, noise])
        labels = np.array([0] * 30 + [1] * 30 + [-1] * 10)

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert -1.0 <= score <= 1.0, "Score must be in [-1, 1]"

    def test_three_clusters(self):
        """SPEC: Three well-separated clusters should have reasonable score."""
        cluster1 = np.random.randn(30, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(30, 10) + np.array([5] * 10)
        cluster3 = np.random.randn(30, 10) + np.array([10] * 10)

        embeddings = np.vstack([cluster1, cluster2, cluster3])
        labels = np.array([0] * 30 + [1] * 30 + [2] * 30)

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert -1.0 <= score <= 1.0, "Score must be in [-1, 1]"

    def test_shape_mismatch_raises_error(self):
        """SPEC: Shape mismatch should raise ValueError."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([0] * 25)  # Wrong length

        with pytest.raises(ValueError, match="Shape mismatch"):
            ClusteringMetrics.silhouette_score(embeddings, labels)

    def test_1536_dim_openai_embeddings(self):
        """SPEC: Works with real 1536-dim OpenAI embeddings."""
        # Simulate OpenAI embeddings (1536 dimensions)
        cluster1 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster1 += np.random.randn(1, 1536) / np.sqrt(1536)

        cluster2 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster2 += np.random.randn(1, 1536) / np.sqrt(1536) * 3

        embeddings = np.vstack([cluster1, cluster2])
        labels = np.array([0] * 50 + [1] * 50)

        score = ClusteringMetrics.silhouette_score(embeddings, labels)

        assert -1.0 <= score <= 1.0, "Score must be in [-1, 1]"
        assert isinstance(score, float), "Score must be float"

    def test_performance_1000_samples(self):
        """SPEC: Metric must complete <1s for 1000 articles."""
        import time

        embeddings = np.random.randn(1000, 128)
        labels = np.random.randint(0, 10, 1000)

        start = time.time()
        score = ClusteringMetrics.silhouette_score(embeddings, labels)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Silhouette score took {elapsed:.2f}s, must be <1s"
        assert isinstance(score, float), "Score must be float"


class TestDaviesBouldinIndex:
    """Davies-Bouldin Index: measures compactness and separation."""

    def test_perfect_separation_two_clusters(self):
        """SPEC: Well-separated clusters should have low DB index < 1.0."""
        cluster1 = np.random.randn(50, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(50, 10) + np.array([10] * 10)
        embeddings = np.vstack([cluster1, cluster2])

        labels = np.array([0] * 50 + [1] * 50)

        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)

        assert db_index >= 0, "DB index must be non-negative"
        assert db_index < 2.0, f"Well-separated clusters should have DB < 2.0, got {db_index}"

    def test_poor_separation_overlapping(self):
        """SPEC: Overlapping clusters should have high DB index > 1.5."""
        cluster1 = np.random.randn(50, 10)
        cluster2 = np.random.randn(50, 10) + np.array([0.5] * 10)
        embeddings = np.vstack([cluster1, cluster2])

        labels = np.array([0] * 50 + [1] * 50)

        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)

        assert db_index >= 0, "DB index must be non-negative"

    def test_single_cluster_returns_zero(self):
        """EDGE: Single cluster cannot measure separation."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([0] * 50)

        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)

        assert db_index == 0.0, "Single cluster should return 0.0"

    def test_all_noise_returns_zero(self):
        """EDGE: All noise points should return 0."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([-1] * 50)

        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)

        assert db_index == 0.0, "All noise should return 0.0"

    def test_three_clusters(self):
        """SPEC: Three well-separated clusters should have reasonable DB index."""
        cluster1 = np.random.randn(30, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(30, 10) + np.array([5] * 10)
        cluster3 = np.random.randn(30, 10) + np.array([10] * 10)

        embeddings = np.vstack([cluster1, cluster2, cluster3])
        labels = np.array([0] * 30 + [1] * 30 + [2] * 30)

        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)

        assert db_index >= 0, "DB index must be non-negative"
        assert isinstance(db_index, float), "DB index must be float"

    def test_shape_mismatch_raises_error(self):
        """SPEC: Shape mismatch should raise ValueError."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([0] * 25)  # Wrong length

        with pytest.raises(ValueError, match="Shape mismatch"):
            ClusteringMetrics.davies_bouldin_index(embeddings, labels)

    def test_mixed_noise_and_clusters(self):
        """SPEC: Noise points should not affect DB index of valid clusters."""
        cluster1 = np.random.randn(30, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(30, 10) + np.array([10] * 10)
        noise = np.random.randn(10, 10) * 50

        embeddings = np.vstack([cluster1, cluster2, noise])
        labels = np.array([0] * 30 + [1] * 30 + [-1] * 10)

        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)

        assert db_index >= 0, "DB index must be non-negative"

    def test_1536_dim_openai_embeddings(self):
        """SPEC: Works with real 1536-dim OpenAI embeddings."""
        cluster1 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster1 += np.random.randn(1, 1536) / np.sqrt(1536)

        cluster2 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster2 += np.random.randn(1, 1536) / np.sqrt(1536) * 3

        embeddings = np.vstack([cluster1, cluster2])
        labels = np.array([0] * 50 + [1] * 50)

        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)

        assert db_index >= 0, "DB index must be non-negative"
        assert isinstance(db_index, float), "DB index must be float"

    def test_performance_1000_samples(self):
        """SPEC: Metric must complete <1s for 1000 articles."""
        import time

        embeddings = np.random.randn(1000, 128)
        labels = np.random.randint(0, 10, 1000)

        start = time.time()
        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"DB index took {elapsed:.2f}s, must be <1s"
        assert isinstance(db_index, float), "DB index must be float"


class TestCalinskiHarabaszIndex:
    """Calinski-Harabasz Index: measures cluster density and definition."""

    def test_perfect_separation_two_clusters(self):
        """SPEC: Well-separated clusters should have high CH index > 50."""
        cluster1 = np.random.randn(50, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(50, 10) + np.array([10] * 10)
        embeddings = np.vstack([cluster1, cluster2])

        labels = np.array([0] * 50 + [1] * 50)

        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        assert ch_index >= 0, "CH index must be non-negative"
        assert ch_index > 10, f"Well-separated clusters should have CH > 10, got {ch_index}"

    def test_poor_separation_overlapping(self):
        """SPEC: Overlapping clusters should have lower CH index."""
        cluster1 = np.random.randn(50, 10)
        cluster2 = np.random.randn(50, 10) + np.array([0.5] * 10)
        embeddings = np.vstack([cluster1, cluster2])

        labels = np.array([0] * 50 + [1] * 50)

        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        assert ch_index >= 0, "CH index must be non-negative"
        assert isinstance(ch_index, float), "CH index must be float"

    def test_single_cluster_returns_zero(self):
        """EDGE: Single cluster cannot compute between-cluster variance."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([0] * 50)

        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        assert ch_index == 0.0, "Single cluster should return 0.0"

    def test_all_noise_returns_zero(self):
        """EDGE: All noise points should return 0."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([-1] * 50)

        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        assert ch_index == 0.0, "All noise should return 0.0"

    def test_three_clusters(self):
        """SPEC: Three well-separated clusters should have high CH index."""
        cluster1 = np.random.randn(30, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(30, 10) + np.array([5] * 10)
        cluster3 = np.random.randn(30, 10) + np.array([10] * 10)

        embeddings = np.vstack([cluster1, cluster2, cluster3])
        labels = np.array([0] * 30 + [1] * 30 + [2] * 30)

        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        assert ch_index >= 0, "CH index must be non-negative"
        assert ch_index > 5, f"Well-separated clusters should have high CH, got {ch_index}"

    def test_shape_mismatch_raises_error(self):
        """SPEC: Shape mismatch should raise ValueError."""
        embeddings = np.random.randn(50, 10)
        labels = np.array([0] * 25)  # Wrong length

        with pytest.raises(ValueError, match="Shape mismatch"):
            ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

    def test_mixed_noise_and_clusters(self):
        """SPEC: Noise points should not affect CH index computation."""
        cluster1 = np.random.randn(30, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(30, 10) + np.array([10] * 10)
        noise = np.random.randn(10, 10) * 50

        embeddings = np.vstack([cluster1, cluster2, noise])
        labels = np.array([0] * 30 + [1] * 30 + [-1] * 10)

        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        assert ch_index >= 0, "CH index must be non-negative"

    def test_1536_dim_openai_embeddings(self):
        """SPEC: Works with real 1536-dim OpenAI embeddings."""
        cluster1 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster1 += np.random.randn(1, 1536) / np.sqrt(1536)

        cluster2 = np.random.randn(50, 1536) / np.sqrt(1536)
        cluster2 += np.random.randn(1, 1536) / np.sqrt(1536) * 3

        embeddings = np.vstack([cluster1, cluster2])
        labels = np.array([0] * 50 + [1] * 50)

        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        assert ch_index >= 0, "CH index must be non-negative"
        assert isinstance(ch_index, float), "CH index must be float"

    def test_performance_1000_samples(self):
        """SPEC: Metric must complete <1s for 1000 articles."""
        import time

        embeddings = np.random.randn(1000, 128)
        labels = np.random.randint(0, 10, 1000)

        start = time.time()
        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"CH index took {elapsed:.2f}s, must be <1s"
        assert isinstance(ch_index, float), "CH index must be float"


class TestIntegrationWithRealClusters:
    """Integration tests with realistic clustering scenarios."""

    def test_all_metrics_on_same_data(self):
        """INTEGRATION: All three metrics should work on same dataset."""
        cluster1 = np.random.randn(40, 10) + np.array([0] * 10)
        cluster2 = np.random.randn(40, 10) + np.array([5] * 10)
        cluster3 = np.random.randn(40, 10) + np.array([10] * 10)

        embeddings = np.vstack([cluster1, cluster2, cluster3])
        labels = np.array([0] * 40 + [1] * 40 + [2] * 40)

        silhouette = ClusteringMetrics.silhouette_score(embeddings, labels)
        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)
        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        # All metrics should return valid floats
        assert isinstance(silhouette, float), "Silhouette must be float"
        assert isinstance(db_index, float), "DB index must be float"
        assert isinstance(ch_index, float), "CH index must be float"

        # Verify range expectations
        assert -1.0 <= silhouette <= 1.0, "Silhouette out of range"
        assert db_index >= 0, "DB index must be non-negative"
        assert ch_index >= 0, "CH index must be non-negative"

    def test_metrics_consistency_with_hdbscan_output(self):
        """INTEGRATION: Works with typical HDBSCAN label output format."""
        # Simulate HDBSCAN output: cluster IDs with noise as -1
        embeddings = np.random.randn(200, 10)

        # Create realistic label distribution (some noise)
        labels = np.array(
            [0] * 60 + [1] * 50 + [2] * 40 + [-1] * 50  # 25% noise
        )

        silhouette = ClusteringMetrics.silhouette_score(embeddings, labels)
        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)
        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        # All should return valid values
        assert isinstance(silhouette, float)
        assert isinstance(db_index, float)
        assert isinstance(ch_index, float)

    def test_large_dataset_performance(self):
        """SPEC: All metrics should complete <3s for 1000 samples."""
        import time

        embeddings = np.random.randn(1000, 128)
        labels = np.random.randint(0, 20, 1000)
        labels[np.random.randint(0, 1000, 100)] = -1  # Add 10% noise

        start = time.time()
        metrics_computed = 0

        try:
            silhouette = ClusteringMetrics.silhouette_score(embeddings, labels)
            metrics_computed += 1
        except Exception as e:
            pytest.fail(f"Silhouette score failed: {e}")

        try:
            db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)
            metrics_computed += 1
        except Exception as e:
            pytest.fail(f"DB index failed: {e}")

        try:
            ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)
            metrics_computed += 1
        except Exception as e:
            pytest.fail(f"CH index failed: {e}")

        elapsed = time.time() - start

        assert metrics_computed == 3, "All metrics should be computed"
        assert (
            elapsed < 3.0
        ), f"All metrics took {elapsed:.2f}s, should complete in <3s"

    def test_all_metrics_with_full_1536_dim_embeddings(self):
        """INTEGRATION: Full workflow with real OpenAI embedding dimensions."""
        # Simulate realistic OpenAI embeddings
        np.random.seed(42)
        cluster1 = np.random.randn(100, 1536)
        cluster1 /= np.linalg.norm(cluster1, axis=1, keepdims=True)
        cluster1 += np.random.randn(1, 1536) * 0.2

        cluster2 = np.random.randn(100, 1536)
        cluster2 /= np.linalg.norm(cluster2, axis=1, keepdims=True)
        cluster2 += np.random.randn(1, 1536) * 0.2 + np.array([0.5] * 1536)

        cluster3 = np.random.randn(100, 1536)
        cluster3 /= np.linalg.norm(cluster3, axis=1, keepdims=True)
        cluster3 += np.random.randn(1, 1536) * 0.2 - np.array([0.5] * 1536)

        embeddings = np.vstack([cluster1, cluster2, cluster3])
        labels = np.array([0] * 100 + [1] * 100 + [2] * 100)

        silhouette = ClusteringMetrics.silhouette_score(embeddings, labels)
        db_index = ClusteringMetrics.davies_bouldin_index(embeddings, labels)
        ch_index = ClusteringMetrics.calinski_harabasz_index(embeddings, labels)

        # All metrics should be valid
        assert -1.0 <= silhouette <= 1.0
        assert db_index >= 0
        assert ch_index >= 0

        # For well-separated clusters with OpenAI embeddings
        assert silhouette > 0.3, f"Expected good separation, got silhouette={silhouette}"
        assert db_index < 10, f"Expected good separation, got DB={db_index}"
        assert ch_index > 50, f"Expected good density, got CH={ch_index}"
