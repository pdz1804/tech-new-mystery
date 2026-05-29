"""Repository for clustering configuration management."""

import asyncio
import logging
import time
from typing import Optional

from pynamodb.exceptions import DoesNotExist

from app.models.clustering import ClusteringParamsModel
from app.utils.time import now_timestamp

logger = logging.getLogger(__name__)

# Simple TTL cache for clustering params to avoid DynamoDB call on every request
_cached_params: Optional[dict] = None
_params_cache_time: Optional[float] = None
_CACHE_TTL_SECONDS = 3600  # 1 hour cache


class ClusteringConfigRepository:
    """Repository for managing clustering configuration parameters."""

    @staticmethod
    def _default_params() -> dict:
        """Return default clustering parameters."""
        return {
            "param_id": "default",
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "min_cluster_size": 5,
            "min_samples": 3,
            "quality_threshold": 0.6,
            "last_updated": now_timestamp(),
        }

    async def get_config(self) -> dict:
        """Get clustering configuration (cached with 1 hour TTL)."""
        global _cached_params, _params_cache_time

        # Check cache
        if _cached_params is not None and _params_cache_time is not None:
            if time.time() - _params_cache_time < _CACHE_TTL_SECONDS:
                logger.debug("Returning cached clustering config")
                return _cached_params

        # Fetch from DynamoDB
        try:
            def _get():
                return ClusteringParamsModel.get("default")

            item = await asyncio.to_thread(_get)
            params = {
                "param_id": item.param_id,
                "silhouette_weight": item.silhouette_weight,
                "davies_bouldin_weight": item.davies_bouldin_weight,
                "calinski_harabasz_weight": item.calinski_harabasz_weight,
                "min_cluster_size": item.min_cluster_size,
                "min_samples": item.min_samples,
                "quality_threshold": item.quality_threshold,
                "last_updated": item.last_updated,
            }
            logger.debug("Clustering config fetched from DynamoDB")
        except DoesNotExist:
            logger.info("Clustering config not found, using defaults")
            params = self._default_params()
        except Exception as e:
            logger.warning(f"Error fetching clustering config, using defaults: {str(e)}")
            params = self._default_params()

        # Update cache
        _cached_params = params
        _params_cache_time = time.time()
        return params

    async def update_config(self, config: dict) -> dict:
        """Update clustering configuration and clear cache."""
        global _cached_params, _params_cache_time

        # Validate input
        config = self._validate_and_normalize(config)

        # Save to DynamoDB
        try:
            def _save():
                item = ClusteringParamsModel("default")
                item.silhouette_weight = config["silhouette_weight"]
                item.davies_bouldin_weight = config["davies_bouldin_weight"]
                item.calinski_harabasz_weight = config["calinski_harabasz_weight"]
                item.min_cluster_size = config["min_cluster_size"]
                item.min_samples = config["min_samples"]
                item.quality_threshold = config["quality_threshold"]
                item.last_updated = now_timestamp()
                item.save()

            await asyncio.to_thread(_save)
            logger.info(f"Clustering config updated: {config}")
        except Exception as e:
            logger.error(f"Error saving clustering config: {str(e)}")
            raise

        # Clear cache
        _cached_params = None
        _params_cache_time = None

        # Return updated config with timestamp
        config["last_updated"] = now_timestamp()
        return config

    async def reset_config(self) -> dict:
        """Reset configuration to defaults."""
        default = self._default_params()
        return await self.update_config(default)

    @staticmethod
    def _validate_and_normalize(config: dict) -> dict:
        """
        Validate and normalize clustering configuration.

        Raises ValueError if validation fails.
        """
        # Extract fields with defaults
        result = {}

        # Get metric weights
        silhouette = float(config.get("silhouette_weight", 0.5))
        davies_bouldin = float(config.get("davies_bouldin_weight", 0.3))
        calinski_harabasz = float(config.get("calinski_harabasz_weight", 0.2))

        # Validate individual weights
        if not (0.0 <= silhouette <= 1.0):
            raise ValueError(f"silhouette_weight must be between 0.0 and 1.0, got {silhouette}")
        if not (0.0 <= davies_bouldin <= 1.0):
            raise ValueError(f"davies_bouldin_weight must be between 0.0 and 1.0, got {davies_bouldin}")
        if not (0.0 <= calinski_harabasz <= 1.0):
            raise ValueError(f"calinski_harabasz_weight must be between 0.0 and 1.0, got {calinski_harabasz}")

        # Validate weights sum to 1.0 (with small tolerance for floating point errors)
        weight_sum = silhouette + davies_bouldin + calinski_harabasz
        if not (0.99 <= weight_sum <= 1.01):  # Allow 1% tolerance
            raise ValueError(
                f"Metric weights must sum to 1.0, got {weight_sum:.4f} "
                f"(silhouette={silhouette}, davies_bouldin={davies_bouldin}, calinski_harabasz={calinski_harabasz})"
            )

        result["silhouette_weight"] = silhouette
        result["davies_bouldin_weight"] = davies_bouldin
        result["calinski_harabasz_weight"] = calinski_harabasz

        # Validate quality threshold
        quality_threshold = float(config.get("quality_threshold", 0.6))
        if not (0.0 <= quality_threshold <= 1.0):
            raise ValueError(f"quality_threshold must be between 0.0 and 1.0, got {quality_threshold}")
        result["quality_threshold"] = quality_threshold

        # Validate cluster size parameters
        min_cluster_size = int(config.get("min_cluster_size", 5))
        if not (3 <= min_cluster_size <= 100):
            raise ValueError(f"min_cluster_size must be between 3 and 100, got {min_cluster_size}")
        result["min_cluster_size"] = min_cluster_size

        min_samples = int(config.get("min_samples", 3))
        if not (1 <= min_samples <= 20):
            raise ValueError(f"min_samples must be between 1 and 20, got {min_samples}")
        result["min_samples"] = min_samples

        return result
