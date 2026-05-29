"""Service for generating clustering evaluation visualization data.

Provides radar/spider chart data for displaying clustering quality metrics
(Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index) across
the latest evaluation runs.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.repositories.clustering_evaluation_repository import ClusteringEvaluationRepository
from app.utils.time import now_timestamp

logger = logging.getLogger(__name__)


class VisualizationService:
    """Service for generating clustering evaluation visualization data.

    Retrieves latest clustering evaluations from DynamoDB and formats them
    as radar chart data with proper normalization for frontend charting.
    """

    def __init__(self, evaluation_repo: Optional[ClusteringEvaluationRepository] = None):
        """Initialize VisualizationService.

        Args:
            evaluation_repo: ClusteringEvaluationRepository instance (lazy-init if None)
        """
        self._evaluation_repo = evaluation_repo

    async def get_metrics_visualization(self, limit: int = 5) -> Dict[str, Any]:
        """Generate visualization data for 3-metric clustering quality plot.

        Fetches latest N evaluations and formats data as radar chart with
        normalized values (0-1 range) for frontend plotting.

        Args:
            limit: Number of latest evaluations to include (default 5, max 20)

        Returns:
            Dictionary with structure:
            {
                "plot_type": "radar",
                "axes": ["silhouette_score", "davies_bouldin_index", "calinski_harabasz_index"],
                "datasets": [
                    {
                        "label": "Evaluation 2026-05-29",
                        "data": [0.65, 0.55, 0.78],  # normalized values
                        "timestamp": timestamp,
                        "raw_values": {
                            "silhouette_score": 0.65,
                            "davies_bouldin_index": 1.5,
                            "calinski_harabasz_index": 350.0
                        }
                    },
                    ...
                ],
                "thresholds": {
                    "silhouette_score": 0.5,
                    "davies_bouldin_index": 1.5,
                    "calinski_harabasz_index": 50
                }
            }
        """
        try:
            # Lazy init repository
            if self._evaluation_repo is None:
                self._evaluation_repo = ClusteringEvaluationRepository()

            # Clamp limit
            limit = min(max(1, limit), 20)

            logger.info(f"[VISUALIZATION] Fetching latest {limit} evaluations")

            # Fetch latest evaluations
            evaluations = await self._evaluation_repo.get_latest_evaluations(limit=limit)

            if not evaluations:
                logger.warning("[VISUALIZATION] No evaluation data found")
                return self._empty_response()

            logger.info(f"[VISUALIZATION] Retrieved {len(evaluations)} evaluations")

            # Extract metrics from evaluations
            datasets = []
            all_silhouette = []
            all_davies_bouldin = []
            all_calinski_harabasz = []

            for evaluation in evaluations:
                # Get the evaluation results (list of k-value results)
                results = evaluation.evaluation_results or []

                if not results:
                    logger.warning(f"[VISUALIZATION] Evaluation {evaluation.evaluation_id} has no results")
                    continue

                # For visualization, we'll use the best (selected) k-value
                # Find the result with the highest weighted_composite_score
                selected_k = evaluation.selected_k_value
                selected_result = next(
                    (r for r in results if r.k_value == selected_k),
                    None
                )

                if not selected_result:
                    logger.warning(
                        f"[VISUALIZATION] Could not find result for selected k={selected_k} "
                        f"in evaluation {evaluation.evaluation_id}"
                    )
                    continue

                # Extract raw metric values
                silhouette = selected_result.silhouette_score
                davies_bouldin = selected_result.davies_bouldin_index
                calinski_harabasz = selected_result.calinski_harabasz_index

                # Track for normalization
                all_silhouette.append(silhouette)
                all_davies_bouldin.append(davies_bouldin)
                all_calinski_harabasz.append(calinski_harabasz)

                datasets.append({
                    "evaluation_id": evaluation.evaluation_id,
                    "timestamp": evaluation.timestamp,
                    "selected_k": selected_k,
                    "raw_values": {
                        "silhouette_score": silhouette,
                        "davies_bouldin_index": davies_bouldin,
                        "calinski_harabasz_index": calinski_harabasz,
                    }
                })

            if not datasets:
                logger.warning("[VISUALIZATION] No valid datasets after filtering")
                return self._empty_response()

            # Calculate normalization parameters
            normalization_params = self._calculate_normalization_params(
                all_silhouette,
                all_davies_bouldin,
                all_calinski_harabasz,
            )

            # Apply normalization and format for frontend
            formatted_datasets = []
            for dataset in datasets:
                raw = dataset["raw_values"]
                normalized = self._normalize_metrics(
                    raw["silhouette_score"],
                    raw["davies_bouldin_index"],
                    raw["calinski_harabasz_index"],
                    normalization_params,
                )

                # Format timestamp to datetime string
                timestamp_dt = datetime.fromtimestamp(dataset["timestamp"])
                label = f"Evaluation {timestamp_dt.strftime('%Y-%m-%d %H:%M')}"

                formatted_datasets.append({
                    "label": label,
                    "data": normalized,
                    "timestamp": dataset["timestamp"],
                    "selected_k": dataset["selected_k"],
                    "raw_values": raw,
                })

            # Define threshold values (from spec)
            thresholds = {
                "silhouette_score": 0.5,
                "davies_bouldin_index": 1.5,
                "calinski_harabasz_index": 50,
            }

            # Normalize thresholds for visualization
            normalized_thresholds = self._normalize_metrics(
                thresholds["silhouette_score"],
                thresholds["davies_bouldin_index"],
                thresholds["calinski_harabasz_index"],
                normalization_params,
            )

            response = {
                "plot_type": "radar",
                "axes": [
                    "silhouette_score",
                    "davies_bouldin_index",
                    "calinski_harabasz_index",
                ],
                "datasets": formatted_datasets,
                "thresholds": {
                    "raw": thresholds,
                    "normalized": [
                        normalized_thresholds[0],
                        normalized_thresholds[1],
                        normalized_thresholds[2],
                    ],
                },
                "normalization_info": {
                    "silhouette_score": {
                        "type": "identity",
                        "description": "Already in 0-1 range",
                    },
                    "davies_bouldin_index": {
                        "type": "invert",
                        "min": normalization_params["davies_bouldin_min"],
                        "max": normalization_params["davies_bouldin_max"],
                        "description": "Inverted (lower is better)",
                    },
                    "calinski_harabasz_index": {
                        "type": "percentile_normalize",
                        "p25": normalization_params["calinski_harabasz_p25"],
                        "p75": normalization_params["calinski_harabasz_p75"],
                        "description": "Normalized using percentiles (higher is better)",
                    },
                },
            }

            logger.info(
                f"[VISUALIZATION] Generated visualization with {len(formatted_datasets)} datasets"
            )

            return response

        except Exception as e:
            logger.error(
                f"[VISUALIZATION] Error generating visualization: {type(e).__name__}: {str(e)}"
            )
            logger.debug("Error details:", exc_info=True)
            raise

    def _calculate_normalization_params(
        self,
        silhouette_scores: List[float],
        davies_bouldin_indices: List[float],
        calinski_harabasz_indices: List[float],
    ) -> Dict[str, float]:
        """Calculate normalization parameters from metric values.

        Args:
            silhouette_scores: List of silhouette scores
            davies_bouldin_indices: List of Davies-Bouldin indices
            calinski_harabasz_indices: List of Calinski-Harabasz indices

        Returns:
            Dictionary with normalization parameters
        """
        params = {}

        # Silhouette: already 0-1 range, no normalization needed
        params["silhouette_min"] = 0.0
        params["silhouette_max"] = 1.0

        # Davies-Bouldin: need to track min/max for inversion
        db_values = np.array(davies_bouldin_indices)
        params["davies_bouldin_min"] = float(np.min(db_values)) if len(db_values) > 0 else 0.0
        params["davies_bouldin_max"] = float(np.max(db_values)) if len(db_values) > 0 else 1.0

        # Calinski-Harabasz: use percentiles for robust normalization
        ch_values = np.array(calinski_harabasz_indices)
        params["calinski_harabasz_p25"] = float(np.percentile(ch_values, 25)) if len(ch_values) > 0 else 0.0
        params["calinski_harabasz_p75"] = float(np.percentile(ch_values, 75)) if len(ch_values) > 0 else 100.0
        params["calinski_harabasz_min"] = float(np.min(ch_values)) if len(ch_values) > 0 else 0.0
        params["calinski_harabasz_max"] = float(np.max(ch_values)) if len(ch_values) > 0 else 100.0

        return params

    def _normalize_metrics(
        self,
        silhouette: float,
        davies_bouldin: float,
        calinski_harabasz: float,
        normalization_params: Dict[str, float],
    ) -> List[float]:
        """Normalize metrics to 0-1 range for visualization.

        Normalization rules:
        - Silhouette Score: Already 0-1, use as-is
        - Davies-Bouldin Index: Invert (lower is better) → 1.0 - normalized_value
        - Calinski-Harabasz Index: Normalize using percentile range

        Args:
            silhouette: Silhouette score (0-1)
            davies_bouldin: Davies-Bouldin index (0 to ∞)
            calinski_harabasz: Calinski-Harabasz index (0 to ∞)
            normalization_params: Dictionary with normalization parameters

        Returns:
            List of 3 normalized values [silhouette_norm, davies_bouldin_norm, calinski_harabasz_norm]
        """
        # Silhouette: already 0-1
        silhouette_norm = np.clip(silhouette, 0.0, 1.0)

        # Davies-Bouldin: invert and normalize
        # First normalize to 0-1 range using min/max from observations
        db_min = normalization_params["davies_bouldin_min"]
        db_max = normalization_params["davies_bouldin_max"]

        if db_max > db_min:
            db_normalized = (davies_bouldin - db_min) / (db_max - db_min)
        else:
            db_normalized = 0.5  # Default if no variation

        # Invert so higher is better
        davies_bouldin_norm = 1.0 - np.clip(db_normalized, 0.0, 1.0)

        # Calinski-Harabasz: normalize using percentile range
        # Values below p25 → 0, between p25-p75 → linear scale, above p75 → 1
        ch_p25 = normalization_params["calinski_harabasz_p25"]
        ch_p75 = normalization_params["calinski_harabasz_p75"]

        if ch_p75 > ch_p25:
            ch_normalized = (calinski_harabasz - ch_p25) / (ch_p75 - ch_p25)
        else:
            # No variation in data, use default normalization
            ch_min = normalization_params["calinski_harabasz_min"]
            ch_max = normalization_params["calinski_harabasz_max"]
            if ch_max > ch_min:
                ch_normalized = (calinski_harabasz - ch_min) / (ch_max - ch_min)
            else:
                ch_normalized = 0.5

        calinski_harabasz_norm = np.clip(ch_normalized, 0.0, 1.0)

        return [
            float(silhouette_norm),
            float(davies_bouldin_norm),
            float(calinski_harabasz_norm),
        ]

    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response structure when no data available.

        Returns:
            Empty visualization response
        """
        return {
            "plot_type": "radar",
            "axes": [
                "silhouette_score",
                "davies_bouldin_index",
                "calinski_harabasz_index",
            ],
            "datasets": [],
            "thresholds": {
                "raw": {
                    "silhouette_score": 0.5,
                    "davies_bouldin_index": 1.5,
                    "calinski_harabasz_index": 50,
                },
                "normalized": [0.5, 0.5, 0.5],
            },
            "normalization_info": {
                "silhouette_score": {
                    "type": "identity",
                    "description": "Already in 0-1 range",
                },
                "davies_bouldin_index": {
                    "type": "invert",
                    "description": "Inverted (lower is better)",
                },
                "calinski_harabasz_index": {
                    "type": "percentile_normalize",
                    "description": "Normalized using percentiles (higher is better)",
                },
            },
        }
