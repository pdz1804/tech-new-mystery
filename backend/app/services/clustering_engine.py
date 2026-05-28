"""HDBSCAN-based clustering engine for article embeddings."""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import hdbscan

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """
    Hierarchical Density-Based Spatial Clustering of Applications with Noise.

    Uses HDBSCAN for clustering article embeddings with automatic noise detection.
    Handles edge cases: small datasets, uniform embeddings, and empty inputs.
    """

    def __init__(
        self,
        min_cluster_size: int = 5,
        min_samples: int = 3,
        metric: str = "cosine",
    ):
        """
        Initialize HDBSCAN clustering engine.

        Args:
            min_cluster_size: Minimum articles per cluster (default: 5)
            min_samples: Minimum core samples in neighborhood (default: 3)
            metric: Distance metric - 'cosine' for embeddings (default)
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.metric = metric
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric=metric,
            allow_single_cluster=False,
        )

    def cluster_articles(
        self, embeddings: np.ndarray, article_ids: List[str]
    ) -> Tuple[Dict[str, int], Dict[str, any]]:
        """
        Cluster articles based on their embeddings.

        Args:
            embeddings: np.ndarray of shape (n_articles, embedding_dim)
                       1536-dimensional embeddings from OpenAI
            article_ids: List[str] of article IDs matching embeddings order

        Returns:
            Tuple of:
            - Dict[article_id, cluster_id]: Cluster assignments (-1 for noise)
            - Dict with statistics:
              - num_clusters: Number of clusters formed
              - num_noise: Count of noise articles (cluster_id=-1)
              - noise_percent: Percentage of noise articles
              - avg_cluster_size: Average articles per cluster
              - cluster_sizes: Dict[cluster_id, count]

        Raises:
            ValueError: If embeddings shape invalid or article_ids mismatch

        Edge Cases:
        - < 5 articles: Return each as noise cluster (-1)
        - All identical embeddings: Return all as noise (-1)
        - 5+ articles: Cluster normally with noise detection
        """
        # Validate inputs
        if len(article_ids) != len(embeddings):
            raise ValueError(
                f"Article count mismatch: {len(article_ids)} IDs vs "
                f"{len(embeddings)} embeddings"
            )

        num_articles = len(article_ids)

        # Edge case: less than minimum cluster size
        if num_articles < self.min_cluster_size:
            logger.warning(
                f"Dataset too small ({num_articles} < {self.min_cluster_size}), "
                "returning all articles as noise"
            )
            result = {aid: -1 for aid in article_ids}
            stats = {
                "num_clusters": 0,
                "num_noise": num_articles,
                "noise_percent": 100.0,
                "avg_cluster_size": 0.0,
                "cluster_sizes": {},
            }
            return result, stats

        # Edge case: empty embeddings
        if embeddings.size == 0:
            logger.warning("Empty embeddings array")
            result = {aid: -1 for aid in article_ids}
            stats = {
                "num_clusters": 0,
                "num_noise": 0,
                "noise_percent": 0.0,
                "avg_cluster_size": 0.0,
                "cluster_sizes": {},
            }
            return result, stats

        # Check for constant embeddings (all identical)
        if np.allclose(embeddings, embeddings[0]):
            logger.warning(
                "All embeddings identical (constant), "
                "returning all articles as noise"
            )
            result = {aid: -1 for aid in article_ids}
            stats = {
                "num_clusters": 0,
                "num_noise": num_articles,
                "noise_percent": 100.0,
                "avg_cluster_size": 0.0,
                "cluster_sizes": {},
            }
            return result, stats

        # Perform clustering
        try:
            labels = self.clusterer.fit_predict(embeddings)
        except Exception as e:
            logger.error(f"HDBSCAN clustering failed: {e}")
            result = {aid: -1 for aid in article_ids}
            stats = {
                "num_clusters": 0,
                "num_noise": num_articles,
                "noise_percent": 100.0,
                "avg_cluster_size": 0.0,
                "cluster_sizes": {},
            }
            return result, stats

        # Build result dictionary
        result = {aid: int(label) for aid, label in zip(article_ids, labels)}

        # Calculate statistics
        unique_labels = set(labels)
        num_clusters = len([l for l in unique_labels if l != -1])
        num_noise = np.sum(labels == -1)
        noise_percent = (num_noise / num_articles * 100.0) if num_articles > 0 else 0.0

        # Calculate cluster sizes
        cluster_sizes = {}
        for label in unique_labels:
            count = np.sum(labels == label)
            cluster_sizes[str(label)] = int(count)

        # Calculate avg cluster size (excluding noise)
        if num_clusters > 0:
            total_clustered = num_articles - num_noise
            avg_cluster_size = (
                total_clustered / num_clusters if num_clusters > 0 else 0.0
            )
        else:
            avg_cluster_size = 0.0

        stats = {
            "num_clusters": num_clusters,
            "num_noise": int(num_noise),
            "noise_percent": float(noise_percent),
            "avg_cluster_size": float(avg_cluster_size),
            "cluster_sizes": cluster_sizes,
        }

        # Log statistics
        logger.info(
            f"Clustering complete: "
            f"clusters={num_clusters}, noise={num_noise} ({noise_percent:.1f}%), "
            f"avg_size={avg_cluster_size:.1f}"
        )

        return result, stats
