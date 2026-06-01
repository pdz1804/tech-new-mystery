"""Build and cache article-level PCA maps for clustered articles."""

import asyncio
import hashlib
import json
import logging

import numpy as np
import redis
from sklearn.decomposition import PCA

from app.api.v1.clusters.schemas import (
    ClusterPCAMapResponse,
    PCAArticlePoint,
    PCAClusterLegendItem,
)
from app.config import settings
from app.repositories.cluster_repository import ClusterRepository
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

CLUSTER_COLORS = [
    "#3B82F6",
    "#8B5CF6",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#06B6D4",
    "#84CC16",
    "#F97316",
    "#14B8A6",
    "#EC4899",
    "#6366F1",
    "#F43F5E",
]


def pca_cache_key(cluster_ids: list[str] | None, limit: int) -> str:
    """Build a stable cache key for a requested PCA map."""
    cluster_part = ",".join(sorted(cluster_ids or ["latest"]))
    digest = hashlib.sha1(f"{cluster_part}:{limit}".encode("utf-8")).hexdigest()
    return f"clusters:pca-map:{digest}"


def get_cached_pca_map(cache_key: str) -> ClusterPCAMapResponse | None:
    """Read a cached PCA map from Redis."""
    client = redis.from_url(settings.redis_url)
    raw = client.get(cache_key)
    if not raw:
        return None
    payload = json.loads(raw)
    return ClusterPCAMapResponse(**payload)


def set_cached_pca_map(cache_key: str, value: ClusterPCAMapResponse, ttl: int = 1800) -> None:
    """Write a PCA map to Redis."""
    client = redis.from_url(settings.redis_url)
    client.setex(cache_key, ttl, json.dumps(value.model_dump()))


async def get_latest_cluster_metadata(
    cluster_repo: ClusterRepository,
    sort_by: str = "size",
):
    """Return all cluster metadata rows for the latest evaluation."""
    all_clusters, _ = await cluster_repo.list_cluster_metadata(limit=10000, sort_by=sort_by)

    if all_clusters:
        eval_ids = [
            c.evaluation_id
            for c in all_clusters
            if hasattr(c, "evaluation_id") and c.evaluation_id is not None
        ]
        if eval_ids:
            latest_eval = max(eval_ids)
            all_clusters = [
                c
                for c in all_clusters
                if hasattr(c, "evaluation_id") and c.evaluation_id == latest_eval
            ]

    return all_clusters


async def build_cluster_pca_map(
    cluster_ids: list[str] | None = None,
    limit: int = 250,
) -> ClusterPCAMapResponse:
    """Build article-level PCA points from cluster article assignments and embeddings."""
    cluster_repo = ClusterRepository()

    if cluster_ids:
        clusters = []
        for cluster_id in cluster_ids[:50]:
            cluster = await cluster_repo.get_cluster_metadata(cluster_id)
            if cluster:
                clusters.append(cluster)
    else:
        clusters = (await get_latest_cluster_metadata(cluster_repo, sort_by="size"))[:50]

    if not clusters:
        return ClusterPCAMapResponse(
            points=[],
            clusters=[],
            total_articles=0,
            total_clusters=0,
            status="ready",
        )

    assignments = []
    cluster_lookup = {}
    per_cluster_limit = max(8, min(40, limit // max(len(clusters), 1) + 4))

    for index, cluster in enumerate(clusters):
        cluster_lookup[cluster.cluster_id] = {
            "label": cluster.label,
            "color": CLUSTER_COLORS[index % len(CLUSTER_COLORS)],
            "article_count": cluster.article_count,
        }
        cluster_assignments, _ = await cluster_repo.get_articles_in_cluster(
            cluster.cluster_id,
            limit=per_cluster_limit,
        )
        assignments.extend(cluster_assignments)

    assignments = assignments[:limit]
    article_ids = [assignment.article_id for assignment in assignments]
    embeddings_by_id = await QdrantService().get_embeddings_by_article_ids(article_ids)
    usable_assignments = [
        assignment for assignment in assignments if assignment.article_id in embeddings_by_id
    ]

    if not usable_assignments:
        return ClusterPCAMapResponse(
            points=[],
            clusters=[],
            total_articles=0,
            total_clusters=0,
            status="ready",
        )

    articles = await cluster_repo.get_articles_by_ids(
        [assignment.article_id for assignment in usable_assignments]
    )
    article_titles = {article.article_id: article.title for article in articles}

    vectors = np.array(
        [embeddings_by_id[assignment.article_id] for assignment in usable_assignments],
        dtype=float,
    )
    projected = (
        np.array([[0.0, 0.0]])
        if len(vectors) == 1
        else PCA(n_components=2, random_state=42).fit_transform(vectors)
    )

    min_xy = projected.min(axis=0)
    max_xy = projected.max(axis=0)
    span = np.where((max_xy - min_xy) == 0, 1, max_xy - min_xy)
    normalized = ((projected - min_xy) / span) * 2 - 1

    points = [
        PCAArticlePoint(
            article_id=assignment.article_id,
            title=article_titles.get(assignment.article_id, "Untitled article"),
            cluster_id=assignment.cluster_id,
            cluster_label=cluster_lookup.get(assignment.cluster_id, {}).get("label", "Cluster"),
            x=float(normalized[index][0]),
            y=float(normalized[index][1]),
            confidence_score=float(assignment.confidence_score),
        )
        for index, assignment in enumerate(usable_assignments)
    ]

    used_cluster_ids = {point.cluster_id for point in points}
    legend = [
        PCAClusterLegendItem(
            cluster_id=cluster_id,
            label=meta["label"],
            color=meta["color"],
            article_count=sum(1 for point in points if point.cluster_id == cluster_id),
        )
        for cluster_id, meta in cluster_lookup.items()
        if cluster_id in used_cluster_ids
    ]

    logger.info(
        "Built PCA map: points=%d clusters=%d",
        len(points),
        len(legend),
    )
    return ClusterPCAMapResponse(
        points=points,
        clusters=legend,
        total_articles=len(points),
        total_clusters=len(legend),
        status="ready",
    )


async def build_and_cache_cluster_pca_map(
    cache_key: str,
    cluster_ids: list[str] | None = None,
    limit: int = 250,
) -> dict:
    """Build a PCA map and store it in Redis."""
    result = await build_cluster_pca_map(cluster_ids=cluster_ids, limit=limit)
    await asyncio.to_thread(set_cached_pca_map, cache_key, result)
    return {
        "success": True,
        "cache_key": cache_key,
        "points": result.total_articles,
        "clusters": result.total_clusters,
    }
