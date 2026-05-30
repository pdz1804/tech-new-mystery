"""Admin endpoints for clustering configuration management."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List
import numpy as np

from app.api.dependencies import require_admin
from app.repositories.clustering_config_repository import ClusteringConfigRepository
from app.repositories.article_repository import ArticleRepository
from app.services.qdrant_service import QdrantService

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


class PCAPoint(BaseModel):
    """Single point in PCA projection."""
    x: float
    y: float
    cluster: int
    article_id: str


class ClusterMetadata(BaseModel):
    """Metadata for a single cluster."""
    count: int
    label: str
    top_keywords: List[str] = []


class PCAVisualizationResponse(BaseModel):
    """PCA visualization response."""
    success: bool
    points: List[PCAPoint]
    clusters: dict[str, ClusterMetadata]
    best_k: int
    silhouette_score: float
    inertia: float
    variance_explained: float
    total_articles: int
    message: str | None = None


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


@router.get("/pca", response_model=PCAVisualizationResponse)
async def get_pca_visualization(
    k_min: int = Query(5, ge=5, le=10, description="Minimum K value"),
    k_max: int = Query(10, ge=5, le=10, description="Maximum K value"),
    _: dict = Depends(require_admin),
) -> PCAVisualizationResponse:
    """
    Get PCA visualization of article embeddings with optimal K selection (admin only).

    Constraints:
    - Min 25 articles, Max 50 articles
    - Min K=5, Max K=10
    - Tries all K values and selects best by silhouette score

    Args:
        k_min: Minimum K value to try (5-10)
        k_max: Maximum K value to try (5-10)

    Returns:
        PCA visualization with 2D points, cluster assignments, and metadata
    """
    try:
        from sklearn.decomposition import PCA
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score

        logger.info(f"[PCA_VIZ] Starting PCA visualization with k_min={k_min}, k_max={k_max}")

        # Ensure k_min <= k_max
        if k_min > k_max:
            k_min, k_max = k_max, k_min

        # Fetch published articles
        article_repo = ArticleRepository()
        articles, _ = await article_repo.list_all(limit=10000, published_only=True)

        if not articles:
            raise HTTPException(status_code=400, detail="No published articles to visualize")

        logger.info(f"[PCA_VIZ] Fetched {len(articles)} articles")

        # Limit to max 50 articles, use all if less than 25
        if len(articles) > 50:
            articles = articles[:50]
            logger.info(f"[PCA_VIZ] Limited to 50 articles")
        elif len(articles) < 25:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 25 articles for visualization (found {len(articles)})"
            )

        article_ids = [a.article_id for a in articles]

        # Fetch embeddings from Qdrant
        qdrant_service = QdrantService()
        qdrant_vecs = await qdrant_service.get_embeddings_by_article_ids(article_ids)

        if not qdrant_vecs:
            raise HTTPException(
                status_code=400,
                detail="No embeddings found in Qdrant. Run clustering first.",
            )

        found_ids = list(qdrant_vecs.keys())
        embeddings_array = np.array([qdrant_vecs[aid] for aid in found_ids])

        logger.info(f"[PCA_VIZ] Got embeddings for {len(found_ids)} articles")

        # Reduce to 2D with PCA
        pca = PCA(n_components=2)
        pca_2d = pca.fit_transform(embeddings_array)

        # Try different K values and find best
        best_k = k_min
        best_score = -1
        best_labels = None
        best_inertia = 0

        for k in range(k_min, k_max + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings_array)

            # Calculate silhouette score
            if k < len(embeddings_array):
                score = silhouette_score(embeddings_array, labels)
            else:
                score = 0.0

            logger.info(f"[PCA_VIZ] K={k}: silhouette_score={score:.4f}, inertia={kmeans.inertia_:.2f}")

            if score > best_score:
                best_score = score
                best_k = k
                best_labels = labels
                best_inertia = kmeans.inertia_

        # Create points list
        points = [
            PCAPoint(
                x=float(pca_2d[i, 0]),
                y=float(pca_2d[i, 1]),
                cluster=int(best_labels[i]),
                article_id=found_ids[i],
            )
            for i in range(len(found_ids))
        ]

        # Create cluster metadata
        clusters_metadata = {}
        for cluster_id in range(best_k):
            cluster_mask = best_labels == cluster_id
            cluster_article_ids = [found_ids[i] for i in range(len(found_ids)) if cluster_mask[i]]
            cluster_articles = [a for a in articles if a.article_id in cluster_article_ids]

            # Get top keywords from cluster articles
            keywords = []
            if cluster_articles:
                # Simple keyword extraction from titles
                all_words = []
                for article in cluster_articles:
                    words = article.title.lower().split()
                    all_words.extend([w for w in words if len(w) > 3])
                # Get most common words (simple approach)
                from collections import Counter
                counter = Counter(all_words)
                keywords = [word for word, _ in counter.most_common(3)]

            clusters_metadata[str(cluster_id)] = ClusterMetadata(
                count=len(cluster_article_ids),
                label=f"Cluster {cluster_id}",
                top_keywords=keywords,
            )

        # Calculate variance explained
        variance_explained = float(np.sum(pca.explained_variance_ratio_))

        logger.info(
            f"[PCA_VIZ] Completed: best_k={best_k}, silhouette={best_score:.4f}, "
            f"variance_explained={variance_explained:.4f}"
        )

        return PCAVisualizationResponse(
            success=True,
            points=points,
            clusters=clusters_metadata,
            best_k=best_k,
            silhouette_score=float(best_score),
            inertia=float(best_inertia),
            variance_explained=variance_explained,
            total_articles=len(found_ids),
            message=f"PCA visualization for {len(found_ids)} articles (K={best_k})",
        )

    except HTTPException:
        raise
    except ImportError:
        logger.error("[PCA_VIZ] sklearn not available")
        raise HTTPException(
            status_code=500,
            detail="PCA visualization requires sklearn library",
        )
    except Exception as e:
        logger.error(f"[PCA_VIZ] Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PCA visualization: {str(e)}",
        )
