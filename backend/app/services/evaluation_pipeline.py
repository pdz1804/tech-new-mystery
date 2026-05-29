"""Clustering evaluation pipeline with quality metrics and k-value selection."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from time import time as timestamp
from datetime import datetime

from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
)

logger = logging.getLogger(__name__)


@dataclass
class MetricResult:
    """Result for a single k-value evaluation."""

    k_value: int
    silhouette_score: float
    davies_bouldin_index: float
    calinski_harabasz_index: float
    num_clusters_formed: int
    avg_cluster_size: float
    noise_percentage: float
    evaluation_time_ms: float
    # Filled in during ranking phase
    silhouette_rank: Optional[int] = None
    davies_bouldin_rank: Optional[int] = None
    calinski_harabasz_rank: Optional[int] = None
    weighted_composite_score: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage."""
        return {
            "k_value": self.k_value,
            "silhouette_score": self.silhouette_score,
            "davies_bouldin_index": self.davies_bouldin_index,
            "calinski_harabasz_index": self.calinski_harabasz_index,
            "silhouette_rank": self.silhouette_rank,
            "davies_bouldin_rank": self.davies_bouldin_rank,
            "calinski_harabasz_rank": self.calinski_harabasz_rank,
            "weighted_composite_score": self.weighted_composite_score,
            "num_clusters_formed": self.num_clusters_formed,
            "avg_cluster_size": self.avg_cluster_size,
            "noise_percentage": self.noise_percentage,
            "evaluation_time_ms": self.evaluation_time_ms,
        }


class EvaluationPipeline:
    """
    Evaluation pipeline for clustering quality assessment.

    Calculates three complementary metrics (Silhouette, Davies-Bouldin, Calinski-Harabasz)
    across a range of k values, ranks them, and computes weighted composite scores
    to select optimal clustering configuration.
    """

    def __init__(
        self,
        silhouette_weight: float = 0.5,
        davies_bouldin_weight: float = 0.3,
        calinski_harabasz_weight: float = 0.2,
    ):
        """
        Initialize evaluation pipeline with metric weights.

        Args:
            silhouette_weight: Weight for Silhouette Score (0-1)
            davies_bouldin_weight: Weight for Davies-Bouldin Index (0-1)
            calinski_harabasz_weight: Weight for Calinski-Harabasz Index (0-1)

        Note:
            Weights should sum to ~1.0. No strict validation - allows flexibility.
        """
        self.silhouette_weight = silhouette_weight
        self.davies_bouldin_weight = davies_bouldin_weight
        self.calinski_harabasz_weight = calinski_harabasz_weight

        # Validate weights sum to reasonable value
        total = silhouette_weight + davies_bouldin_weight + calinski_harabasz_weight
        if total <= 0:
            raise ValueError("Sum of weights must be positive")
        if not (0.8 <= total <= 1.2):
            logger.warning(
                f"Weights sum to {total}, expected ~1.0. "
                f"Scores will be scaled accordingly."
            )

    def evaluate_clustering(
        self,
        embeddings: np.ndarray,
        cluster_assignments: Dict[str, int],
        article_ids: List[str],
        k_min: int = 5,
        k_max: int = 100,
    ) -> Tuple[List[MetricResult], Dict]:
        """
        Evaluate clustering quality across a range of k values.

        This is the MAIN entry point. For each k in [k_min, k_max]:
        1. Re-cluster data with target k value
        2. Calculate all three metrics
        3. Collect results

        Args:
            embeddings: np.ndarray of shape (n_articles, embedding_dim)
            cluster_assignments: Dict[article_id, cluster_id] from HDBSCAN
            article_ids: List[str] of article IDs in order matching embeddings
            k_min: Minimum k value to evaluate (default: 5)
            k_max: Maximum k value to evaluate (default: 100)

        Returns:
            Tuple of:
            - List[MetricResult]: Results for each k value
            - Dict: Summary statistics with selected k_value and best_composite_score
        """
        logger.info(f"Starting clustering evaluation: k_min={k_min}, k_max={k_max}")

        if len(embeddings) < k_min:
            logger.warning(
                f"Only {len(embeddings)} articles available, less than k_min={k_min}. "
                f"Adjusting k_max to {len(embeddings)}"
            )
            k_max = min(k_max, len(embeddings))

        # Step 1: Calculate metrics for each k value
        results = []
        for k in range(k_min, k_max + 1):
            logger.debug(f"Evaluating k={k}")
            result = self._evaluate_single_k(embeddings, article_ids, k)
            if result:
                results.append(result)

        if not results:
            logger.warning("No valid evaluation results generated")
            return [], {
                "selected_k_value": None,
                "best_composite_score": 0.0,
                "evaluation_results": [],
                "metrics_summary": {},
            }

        logger.info(f"Generated {len(results)} evaluation results")

        # Step 2: Rank metrics across all k values
        self._rank_metrics(results)

        # Step 3: Calculate composite scores
        self._calculate_composite_scores(results)

        # Step 4: Find best k value
        best_result = max(results, key=lambda r: r.weighted_composite_score)
        logger.info(
            f"Best k={best_result.k_value} with composite_score="
            f"{best_result.weighted_composite_score:.4f}"
        )

        # Step 5: Generate summary statistics
        summary = self._generate_summary(results, best_result)

        return results, summary

    def _evaluate_single_k(
        self,
        embeddings: np.ndarray,
        article_ids: List[str],
        k: int,
    ) -> Optional[MetricResult]:
        """
        Evaluate clustering quality for a single k value.

        Steps:
        1. Re-cluster with k-means to get exactly k clusters
        2. Calculate all three metrics
        3. Return MetricResult

        Args:
            embeddings: Full embeddings array (n_articles, embedding_dim)
            article_ids: Article IDs in order matching embeddings
            k: Target number of clusters

        Returns:
            MetricResult or None if evaluation fails
        """
        try:
            start_time = timestamp()

            # Use K-Means to get exactly k clusters
            from sklearn.cluster import KMeans

            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            # Handle edge case: if all articles assigned to one cluster
            unique_clusters = len(np.unique(labels))
            if unique_clusters < 2:
                logger.debug(f"k={k}: All articles in single cluster, skipping metrics")
                return None

            # Calculate silhouette score
            sil_score = silhouette_score(embeddings, labels, metric="euclidean")

            # Calculate davies-bouldin index
            db_index = davies_bouldin_score(embeddings, labels)

            # Calculate calinski-harabasz index
            ch_index = calinski_harabasz_score(embeddings, labels)

            # Calculate cluster statistics
            unique_labels, counts = np.unique(labels, return_counts=True)
            avg_cluster_size = float(np.mean(counts))
            noise_percentage = 0.0  # K-Means doesn't produce noise

            eval_time_ms = (timestamp() - start_time) * 1000

            result = MetricResult(
                k_value=k,
                silhouette_score=float(sil_score),
                davies_bouldin_index=float(db_index),
                calinski_harabasz_index=float(ch_index),
                num_clusters_formed=unique_clusters,
                avg_cluster_size=avg_cluster_size,
                noise_percentage=noise_percentage,
                evaluation_time_ms=eval_time_ms,
            )

            logger.debug(
                f"k={k}: silhouette={sil_score:.4f}, db={db_index:.4f}, ch={ch_index:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Error evaluating k={k}: {e}")
            return None

    def _rank_metrics(self, results: List[MetricResult]) -> None:
        """
        Rank each metric across all k values.

        Ranking rules:
        - Silhouette Score: Higher is better → rank by value descending
        - Davies-Bouldin Index: Lower is better → rank by value ascending
        - Calinski-Harabasz Index: Higher is better → rank by value descending

        Ranking is 1-indexed (rank 1 = best).

        Args:
            results: List of MetricResult objects (modified in-place)
        """
        if not results:
            return

        # Rank silhouette score (higher is better)
        sorted_by_sil = sorted(
            results,
            key=lambda r: r.silhouette_score,
            reverse=True,
        )
        for rank, result in enumerate(sorted_by_sil, 1):
            result.silhouette_rank = rank

        # Rank davies-bouldin index (lower is better)
        sorted_by_db = sorted(
            results,
            key=lambda r: r.davies_bouldin_index,
            reverse=False,  # Ascending for lower is better
        )
        for rank, result in enumerate(sorted_by_db, 1):
            result.davies_bouldin_rank = rank

        # Rank calinski-harabasz index (higher is better)
        sorted_by_ch = sorted(
            results,
            key=lambda r: r.calinski_harabasz_index,
            reverse=True,
        )
        for rank, result in enumerate(sorted_by_ch, 1):
            result.calinski_harabasz_rank = rank

        logger.debug(f"Ranking complete for {len(results)} k values")

    def _calculate_composite_scores(self, results: List[MetricResult]) -> None:
        """
        Calculate weighted composite score for each k value.

        Formula:
            composite_score = Σ (weight_i / rank_i)

        This inverse ranking ensures rank 1 (best) contributes highest.

        Args:
            results: List of MetricResult objects (modified in-place)
        """
        for result in results:
            if (
                result.silhouette_rank is None
                or result.davies_bouldin_rank is None
                or result.calinski_harabasz_rank is None
            ):
                logger.warning(f"Missing ranks for k={result.k_value}")
                result.weighted_composite_score = 0.0
                continue

            # Calculate contributions
            sil_contribution = self.silhouette_weight / result.silhouette_rank
            db_contribution = self.davies_bouldin_weight / result.davies_bouldin_rank
            ch_contribution = self.calinski_harabasz_weight / result.calinski_harabasz_rank

            # Sum contributions
            composite = sil_contribution + db_contribution + ch_contribution
            result.weighted_composite_score = float(composite)

            logger.debug(
                f"k={result.k_value}: composite={composite:.4f} "
                f"(sil_contrib={sil_contribution:.4f}, "
                f"db_contrib={db_contribution:.4f}, "
                f"ch_contrib={ch_contribution:.4f})"
            )

    def _generate_summary(
        self,
        results: List[MetricResult],
        best_result: MetricResult,
    ) -> Dict:
        """
        Generate summary statistics for evaluation.

        Args:
            results: All evaluation results
            best_result: Best performing k value

        Returns:
            Dict with summary information
        """
        # Extract metric values
        sil_scores = [r.silhouette_score for r in results]
        db_indices = [r.davies_bouldin_index for r in results]
        ch_indices = [r.calinski_harabasz_index for r in results]
        composite_scores = [r.weighted_composite_score for r in results]

        # Calculate statistics
        def stats(values):
            arr = np.array(values)
            return {
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
                "std_dev": float(np.std(arr)),
            }

        summary = {
            "selected_k_value": best_result.k_value,
            "best_composite_score": best_result.weighted_composite_score,
            "evaluation_results": [r.to_dict() for r in results],
            "metrics_summary": {
                "silhouette_score": stats(sil_scores),
                "davies_bouldin_index": stats(db_indices),
                "calinski_harabasz_index": stats(ch_indices),
                "composite_score": stats(composite_scores),
            },
        }

        return summary
