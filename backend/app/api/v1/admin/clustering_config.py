"""Admin endpoints for clustering configuration management."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import require_admin
from app.repositories.clustering_config_repository import ClusteringConfigRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clustering", tags=["admin-clustering"])


class ClusteringWeightItem(BaseModel):
    """Clustering metric weight item."""
    silhouette_weight: float = Field(
        ge=0.0, le=1.0, description="Weight for silhouette score (0-1)"
    )
    davies_bouldin_weight: float = Field(
        ge=0.0, le=1.0, description="Weight for davies-bouldin index (0-1)"
    )
    calinski_harabasz_weight: float = Field(
        ge=0.0, le=1.0, description="Weight for calinski-harabasz index (0-1)"
    )


class ClusteringParamsItem(BaseModel):
    """Clustering parameters item."""
    min_cluster_size: int = Field(ge=3, le=100, description="Minimum articles per cluster (3-100)")
    min_samples: int = Field(ge=1, le=20, description="Minimum samples for HDBSCAN (1-20)")


class ClusteringQualityItem(BaseModel):
    """Clustering quality threshold item."""
    quality_threshold: float = Field(ge=0.0, le=1.0, description="Quality score threshold (0-1)")


class ClusteringConfigRequest(BaseModel):
    """Request schema for updating clustering configuration."""
    silhouette_weight: float = Field(
        ge=0.0, le=1.0, description="Weight for silhouette score (0-1)"
    )
    davies_bouldin_weight: float = Field(
        ge=0.0, le=1.0, description="Weight for davies-bouldin index (0-1)"
    )
    calinski_harabasz_weight: float = Field(
        ge=0.0, le=1.0, description="Weight for calinski-harabasz index (0-1)"
    )
    quality_threshold: float = Field(
        ge=0.0, le=1.0, description="Quality score threshold (0-1)"
    )
    min_cluster_size: int = Field(
        ge=3, le=100, description="Minimum articles per cluster (3-100)"
    )
    min_samples: int = Field(
        ge=1, le=20, description="Minimum samples for HDBSCAN (1-20)"
    )


class ClusteringConfigResponse(BaseModel):
    """Response schema for clustering configuration."""
    silhouette_weight: float
    davies_bouldin_weight: float
    calinski_harabasz_weight: float
    min_cluster_size: int
    min_samples: int
    quality_threshold: float
    last_updated: int


class ClusteringConfigErrorResponse(BaseModel):
    """Error response with details."""
    error: str
    details: str | None = None


@router.get("/config", response_model=ClusteringConfigResponse)
async def get_clustering_config(
    _: dict = Depends(require_admin),
) -> ClusteringConfigResponse:
    """
    Get current clustering configuration (admin only).

    Returns:
        ClusteringConfigResponse: Current configuration with metric weights and parameters
    """
    repo = ClusteringConfigRepository()
    config = await repo.get_config()

    return ClusteringConfigResponse(
        silhouette_weight=config["silhouette_weight"],
        davies_bouldin_weight=config["davies_bouldin_weight"],
        calinski_harabasz_weight=config["calinski_harabasz_weight"],
        min_cluster_size=config["min_cluster_size"],
        min_samples=config["min_samples"],
        quality_threshold=config["quality_threshold"],
        last_updated=config["last_updated"],
    )


@router.put("/config", response_model=ClusteringConfigResponse)
async def update_clustering_config(
    request: ClusteringConfigRequest,
    _: dict = Depends(require_admin),
) -> ClusteringConfigResponse:
    """
    Update clustering configuration (admin only).

    Validates:
    - Weights sum to 1.0
    - Each weight in range 0.0-1.0
    - Quality threshold in range 0.0-1.0
    - min_cluster_size in range 3-100
    - min_samples in range 1-20

    Args:
        request: ClusteringConfigRequest with new configuration values

    Returns:
        ClusteringConfigResponse: Updated configuration

    Raises:
        HTTPException(400): If validation fails
    """
    repo = ClusteringConfigRepository()

    try:
        config = await repo.update_config(request.model_dump())
    except ValueError as e:
        logger.warning(f"Validation error updating clustering config: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating clustering config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update clustering configuration",
        )

    return ClusteringConfigResponse(
        silhouette_weight=config["silhouette_weight"],
        davies_bouldin_weight=config["davies_bouldin_weight"],
        calinski_harabasz_weight=config["calinski_harabasz_weight"],
        min_cluster_size=config["min_cluster_size"],
        min_samples=config["min_samples"],
        quality_threshold=config["quality_threshold"],
        last_updated=config["last_updated"],
    )


@router.post("/config/reset", response_model=ClusteringConfigResponse)
async def reset_clustering_config(
    _: dict = Depends(require_admin),
) -> ClusteringConfigResponse:
    """
    Reset clustering configuration to default values (admin only).

    Default values:
    - silhouette_weight: 0.5
    - davies_bouldin_weight: 0.3
    - calinski_harabasz_weight: 0.2
    - min_cluster_size: 5
    - min_samples: 3
    - quality_threshold: 0.6

    Returns:
        ClusteringConfigResponse: Reset configuration
    """
    repo = ClusteringConfigRepository()

    try:
        config = await repo.reset_config()
        logger.info("Clustering config reset to defaults")
    except Exception as e:
        logger.error(f"Error resetting clustering config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to reset clustering configuration",
        )

    return ClusteringConfigResponse(
        silhouette_weight=config["silhouette_weight"],
        davies_bouldin_weight=config["davies_bouldin_weight"],
        calinski_harabasz_weight=config["calinski_harabasz_weight"],
        min_cluster_size=config["min_cluster_size"],
        min_samples=config["min_samples"],
        quality_threshold=config["quality_threshold"],
        last_updated=config["last_updated"],
    )
