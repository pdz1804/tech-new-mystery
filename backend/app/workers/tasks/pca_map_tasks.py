"""Worker tasks for precomputing article embedding PCA maps."""

import asyncio
import logging

from app.services.cluster_pca_map_service import build_and_cache_cluster_pca_map
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.generate_cluster_pca_map",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
)
def generate_cluster_pca_map(
    self,
    cache_key: str,
    cluster_ids: list[str] | None = None,
    limit: int = 250,
) -> dict:
    """Precompute and cache article-level PCA map data."""
    try:
        return asyncio.run(
            build_and_cache_cluster_pca_map(
                cache_key=cache_key,
                cluster_ids=cluster_ids,
                limit=limit,
            )
        )
    except Exception as exc:
        logger.error("[PCA_MAP] Task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
