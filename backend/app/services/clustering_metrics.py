"""Clustering quality evaluation metrics.

Provides three complementary metrics for evaluating clustering quality:
- Silhouette Score: cohesion vs separation (-1 to 1, higher is better)
- Davies-Bouldin Index: compactness and separation (0 to ∞, lower is better)
- Calinski-Harabasz Index: cluster density and definition (0 to ∞, higher is better)
"""

import logging
import numpy as np
from typing import Tuple

logger = logging.getLogger(__name__)


class ClusteringMetrics:
    """Clustering quality evaluation metrics.

    All metrics work with:
    - embeddings: np.ndarray of shape (n_samples, n_features)
    - labels: np.ndarray of shape (n_samples,) with cluster IDs
      - Noise points should have label -1
      - Valid clusters have non-negative integer IDs
    """

    @staticmethod
    def silhouette_score(embeddings: np.ndarray, labels: np.ndarray) -> float:
        """
        Calculate silhouette score for clustering quality.

        Measures how similar an article is to its own cluster vs other clusters.

        Range: -1 to 1
        - > 0.7: Excellent cluster separation
        - 0.5 - 0.7: Good cluster structure
        - 0.25 - 0.5: Weak cluster structure
        - < 0.25: Overlapping clusters

        Formula: For each point i: s(i) = (b(i) - a(i)) / max(a(i), b(i))
        - a(i) = mean intra-cluster distance (distance to cluster members)
        - b(i) = mean inter-cluster distance (distance to nearest other cluster)

        Args:
            embeddings: np.ndarray of shape (n_samples, n_features)
            labels: np.ndarray of shape (n_samples,) with cluster IDs

        Returns:
            float: Mean silhouette coefficient

        Raises:
            ValueError: If inputs are invalid or clustering is degenerate
        """
        embeddings = np.asarray(embeddings, dtype=np.float32)
        labels = np.asarray(labels, dtype=np.int32)

        # Validate inputs
        if embeddings.shape[0] != labels.shape[0]:
            raise ValueError(
                f"Shape mismatch: {embeddings.shape[0]} samples vs {labels.shape[0]} labels"
            )

        n_samples = embeddings.shape[0]

        # Edge case: single sample
        if n_samples == 1:
            return 0.0

        # Get unique non-noise labels
        unique_labels = np.unique(labels[labels != -1])
        n_clusters = len(unique_labels)

        # Edge case: no valid clusters (all noise)
        if n_clusters == 0:
            logger.warning("No valid clusters found (all noise)")
            return 0.0

        # Edge case: single cluster (cannot compute separation)
        if n_clusters == 1:
            logger.warning("Only one cluster found, silhouette score = 0.0")
            return 0.0

        silhouette_scores = np.zeros(n_samples)

        # Compute pairwise Euclidean distances
        distances = _compute_pairwise_distances(embeddings)

        # For each point, compute silhouette coefficient
        for i in range(n_samples):
            label_i = labels[i]

            # Skip noise points
            if label_i == -1:
                silhouette_scores[i] = 0.0
                continue

            # Get indices of points in same cluster
            same_cluster = np.where(labels == label_i)[0]

            # a(i): mean distance to other points in same cluster
            if len(same_cluster) > 1:
                dist_to_same = distances[i, same_cluster]
                dist_to_same = dist_to_same[dist_to_same > 0]  # Exclude distance to self
                a_i = np.mean(dist_to_same) if len(dist_to_same) > 0 else 0.0
            else:
                a_i = 0.0

            # b(i): min mean distance to points in other clusters
            b_i = np.inf
            for label_j in unique_labels:
                if label_j == label_i:
                    continue

                other_cluster = np.where(labels == label_j)[0]
                dist_to_other = distances[i, other_cluster]
                mean_dist = np.mean(dist_to_other)

                if mean_dist < b_i:
                    b_i = mean_dist

            # Compute s(i) = (b(i) - a(i)) / max(a(i), b(i))
            max_dist = max(a_i, b_i)
            if max_dist > 0:
                silhouette_scores[i] = (b_i - a_i) / max_dist
            else:
                silhouette_scores[i] = 0.0

        # Return mean silhouette coefficient (including noise points)
        return float(np.mean(silhouette_scores))

    @staticmethod
    def davies_bouldin_index(embeddings: np.ndarray, labels: np.ndarray) -> float:
        """
        Calculate Davies-Bouldin Index for clustering quality.

        Measures average ratio of within-cluster to between-cluster distances.
        Combines cluster compactness and separation into a single metric.

        Range: 0 to ∞ (lower is better)
        - < 1.0: Excellent cluster separation
        - 1.0 - 2.0: Good cluster separation
        - > 2.0: Poor cluster separation

        Formula: DB = (1/k) × Σ max(R_ij) where R_ij = (σ_i + σ_j) / d(c_i, c_j)
        - σ_i = average distance of points in cluster i to centroid
        - d(c_i, c_j) = distance between cluster centroids i and j
        - max(R_ij) = largest ratio for cluster i with any other cluster j

        Args:
            embeddings: np.ndarray of shape (n_samples, n_features)
            labels: np.ndarray of shape (n_samples,) with cluster IDs

        Returns:
            float: Davies-Bouldin Index

        Raises:
            ValueError: If inputs are invalid or clustering is degenerate
        """
        embeddings = np.asarray(embeddings, dtype=np.float32)
        labels = np.asarray(labels, dtype=np.int32)

        # Validate inputs
        if embeddings.shape[0] != labels.shape[0]:
            raise ValueError(
                f"Shape mismatch: {embeddings.shape[0]} samples vs {labels.shape[0]} labels"
            )

        # Get unique non-noise labels
        unique_labels = np.unique(labels[labels != -1])
        n_clusters = len(unique_labels)

        # Edge case: no valid clusters
        if n_clusters == 0:
            logger.warning("No valid clusters found (all noise)")
            return 0.0

        # Edge case: single cluster
        if n_clusters == 1:
            logger.warning("Only one cluster found, DB index = 0.0")
            return 0.0

        # Compute cluster centroids and compactness
        centroids = {}
        compactness = {}  # σ_i for each cluster

        for label in unique_labels:
            mask = labels == label
            cluster_points = embeddings[mask]
            centroid = np.mean(cluster_points, axis=0)
            centroids[label] = centroid

            # σ_i = average distance from points to centroid
            distances_to_centroid = np.linalg.norm(cluster_points - centroid, axis=1)
            compactness[label] = np.mean(distances_to_centroid)

        # Compute Davies-Bouldin Index
        db_values = []

        for i, label_i in enumerate(unique_labels):
            max_ratio = 0.0

            for label_j in unique_labels:
                if label_i == label_j:
                    continue

                # R_ij = (σ_i + σ_j) / d(c_i, c_j)
                sigma_sum = compactness[label_i] + compactness[label_j]

                # Distance between centroids
                centroid_distance = np.linalg.norm(
                    centroids[label_i] - centroids[label_j]
                )

                if centroid_distance > 0:
                    ratio = sigma_sum / centroid_distance
                else:
                    ratio = 0.0

                if ratio > max_ratio:
                    max_ratio = ratio

            db_values.append(max_ratio)

        # DB = (1/k) × Σ max(R_ij)
        db_index = np.mean(db_values) if db_values else 0.0
        return float(db_index)

    @staticmethod
    def calinski_harabasz_index(embeddings: np.ndarray, labels: np.ndarray) -> float:
        """
        Calculate Calinski-Harabasz Index for clustering quality.

        Measures ratio of between-cluster variance to within-cluster variance.
        Higher values indicate denser and better-separated clusters.

        Range: 0 to ∞ (higher is better)
        - > 100: Very dense, well-separated clusters
        - 50 - 100: Good cluster density and definition
        - 25 - 50: Moderate cluster quality
        - < 25: Poor cluster definition

        Formula: CH = (SS_between / (k-1)) / (SS_within / (n-k))
        - SS_between = sum of squared distances of cluster centroids from global centroid
        - SS_within = sum of squared distances within clusters
        - k = number of clusters
        - n = total number of articles

        Args:
            embeddings: np.ndarray of shape (n_samples, n_features)
            labels: np.ndarray of shape (n_samples,) with cluster IDs

        Returns:
            float: Calinski-Harabasz Index

        Raises:
            ValueError: If inputs are invalid or clustering is degenerate
        """
        embeddings = np.asarray(embeddings, dtype=np.float32)
        labels = np.asarray(labels, dtype=np.int32)

        # Validate inputs
        if embeddings.shape[0] != labels.shape[0]:
            raise ValueError(
                f"Shape mismatch: {embeddings.shape[0]} samples vs {labels.shape[0]} labels"
            )

        n_samples = embeddings.shape[0]

        # Get unique non-noise labels
        unique_labels = np.unique(labels[labels != -1])
        n_clusters = len(unique_labels)

        # Edge case: no valid clusters or single cluster
        if n_clusters < 2:
            logger.warning(
                f"Need at least 2 clusters for Calinski-Harabasz, found {n_clusters}"
            )
            return 0.0

        # Compute global centroid
        global_centroid = np.mean(embeddings, axis=0)

        # Compute SS_between and SS_within
        ss_between = 0.0
        ss_within = 0.0

        for label in unique_labels:
            mask = labels == label
            cluster_points = embeddings[mask]
            n_k = np.sum(mask)

            # Cluster centroid
            centroid = np.mean(cluster_points, axis=0)

            # SS_between: sum of squared distances of cluster centroid from global centroid
            # weighted by cluster size
            ss_between += n_k * np.sum((centroid - global_centroid) ** 2)

            # SS_within: sum of squared distances within cluster
            ss_within += np.sum((cluster_points - centroid) ** 2)

        # CH = (SS_between / (k-1)) / (SS_within / (n-k))
        # Avoid division by zero
        if ss_within == 0:
            logger.warning("SS_within is zero (possibly uniform clusters)")
            return 0.0

        ch_index = (ss_between / (n_clusters - 1)) / (ss_within / (n_samples - n_clusters))
        return float(ch_index)


def _compute_pairwise_distances(embeddings: np.ndarray) -> np.ndarray:
    """
    Compute pairwise Euclidean distances efficiently.

    Args:
        embeddings: np.ndarray of shape (n_samples, n_features)

    Returns:
        np.ndarray of shape (n_samples, n_samples) with pairwise distances
    """
    n_samples = embeddings.shape[0]

    # Use vectorized computation: ||a - b||^2 = ||a||^2 + ||b||^2 - 2*a·b
    sq_norm = np.sum(embeddings ** 2, axis=1)
    distances = sq_norm[:, np.newaxis] + sq_norm[np.newaxis, :] - 2 * np.dot(
        embeddings, embeddings.T
    )

    # Ensure non-negative (numerical errors can cause small negatives)
    distances = np.maximum(distances, 0)

    # Take square root to get actual Euclidean distances
    distances = np.sqrt(distances)

    return distances
