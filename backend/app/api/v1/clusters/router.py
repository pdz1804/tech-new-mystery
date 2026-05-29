"""Cluster API endpoints for browsing semantic article clusters."""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.v1.clusters.schemas import (
    ClusterListResponse,
    ClusterDetail,
    ClusterArticlesResponse,
    TrendingClustersResponse,
    PaginationInfo,
    ClusterSummary,
    TrendingClusterSummary,
    ArticleInCluster,
    TopArticleItem,
    ClusterMetrics,
)
from app.repositories.cluster_repository import ClusterRepository
from app.repositories.article_repository import ArticleRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clusters", tags=["clusters"])


def get_cluster_repo() -> ClusterRepository:
    """Dependency for cluster repository."""
    return ClusterRepository()


def get_article_repo() -> ArticleRepository:
    """Dependency for article repository."""
    return ArticleRepository()


@router.get("", response_model=ClusterListResponse)
async def list_clusters(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("size", regex="^(size|recency|diversity)$", description="Sort by: size, recency, or diversity"),
    cluster_repo: ClusterRepository = Depends(get_cluster_repo),
) -> ClusterListResponse:
    """List all active clusters with metadata.

    Query Parameters:
    - page: Page number (1-indexed, default 1)
    - page_size: Items per page (1-100, default 20)
    - sort_by: Sort field - "size", "recency", or "diversity" (default "size")

    Returns:
    - List of clusters with pagination metadata
    """
    logger.info(
        f"[CLUSTERS.LIST] Request: page={page}, page_size={page_size}, sort_by={sort_by}"
    )

    try:
        # Get total count
        total_count = await cluster_repo.count_clusters()

        # Calculate pagination
        total_pages = (total_count + page_size - 1) // page_size
        if page > total_pages and total_pages > 0:
            raise HTTPException(status_code=400, detail="Page number exceeds total pages")

        # Get clusters for this page
        # For simple offset-based pagination, we fetch all and slice
        # For production, consider implementing cursor-based pagination
        all_clusters, _ = await cluster_repo.list_cluster_metadata(
            limit=total_count if total_count > 0 else 1,
            sort_by=sort_by,
        )

        # Apply pagination
        offset = (page - 1) * page_size
        page_clusters = all_clusters[offset : offset + page_size]

        # Convert to response schema
        items = [
            ClusterSummary(
                id=cluster.cluster_id,
                label=cluster.label,
                description=cluster.description,
                article_count=cluster.article_count,
                top_articles=[
                    TopArticleItem(
                        id=article.article_id,
                        title=article.title,
                        engagement_score=float(article.engagement_score),
                    )
                    for article in (cluster.top_articles or [])
                ],
                confidence=None,
                keywords=cluster.keywords or [],
                size_category=cluster.size_category,
                diversity_score=float(cluster.diversity_score),
                created_at=float(cluster.created_at or cluster.updated_at),
                updated_at=float(cluster.updated_at),
            )
            for cluster in page_clusters
        ]

        pagination = PaginationInfo(
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        logger.info(
            f"[CLUSTERS.LIST] Returned {len(items)} clusters, page {page}/{total_pages}"
        )
        return ClusterListResponse(clusters=items, pagination=pagination)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLUSTERS.LIST] Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list clusters")


@router.get("/trending", response_model=TrendingClustersResponse)
async def get_trending_clusters(
    limit: int = Query(5, ge=1, description="Number of clusters (capped at 5)"),
    cluster_repo: ClusterRepository = Depends(get_cluster_repo),
) -> TrendingClustersResponse:
    """Get top trending clusters sorted by engagement and recency.

    Query Parameters:
    - limit: Maximum clusters to return (1-10, default 5)

    Returns:
    - List of up to 5 trending cluster summaries
    """
    logger.info(f"[CLUSTERS.TRENDING] Request: limit={limit}")

    try:
        # Limit to 5 max per spec
        limit = min(limit, 5)

        trending = await cluster_repo.get_trending_clusters(limit=limit)

        items = [
            TrendingClusterSummary(
                cluster_id=cluster.cluster_id,
                label=cluster.label,
                article_count=cluster.article_count,
                trending_rank=idx + 1,
                momentum_score=cluster.diversity_score,
                engagement_trend="STABLE",
                articles_added_last_hour=0,
                keywords=cluster.keywords or [],
            )
            for idx, cluster in enumerate(trending)
        ]

        response = TrendingClustersResponse(trending_clusters=items)

        logger.info(f"[CLUSTERS.TRENDING] Returned {len(items)} trending clusters")
        return response

    except Exception as e:
        logger.error(f"[CLUSTERS.TRENDING] Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get trending clusters")


@router.get("/{cluster_id}", response_model=ClusterDetail)
async def get_cluster_detail(
    cluster_id: str,
    page: int = Query(1, ge=1, description="Page number for articles"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    cluster_repo: ClusterRepository = Depends(get_cluster_repo),
    article_repo: ArticleRepository = Depends(get_article_repo),
) -> ClusterDetail:
    """Retrieve detailed cluster information with paginated articles.

    Path Parameters:
    - cluster_id: Unique cluster identifier

    Query Parameters:
    - page: Page number for articles (1-indexed, default 1)
    - page_size: Articles per page (1-100, default 20)

    Returns:
    - Cluster details with paginated article list
    """
    logger.info(
        f"[CLUSTERS.DETAIL] Request: cluster_id={cluster_id}, page={page}, page_size={page_size}"
    )

    try:
        # Fetch cluster metadata
        cluster = await cluster_repo.get_cluster_metadata(cluster_id)
        if not cluster:
            logger.warning(f"[CLUSTERS.DETAIL] Cluster not found: {cluster_id}")
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Fetch articles in cluster
        article_assignments, next_key = await cluster_repo.get_articles_in_cluster(
            cluster_id, limit=max(page * page_size, page_size)
        )

        # Apply pagination
        offset = (page - 1) * page_size
        page_assignments = article_assignments[offset : offset + page_size]

        # Get article details
        article_ids = [a.article_id for a in page_assignments]
        articles = await cluster_repo.get_articles_by_ids(article_ids) if article_ids else []

        # Create mapping of article_id to article
        article_map = {a.article_id: a for a in articles}

        # Build article response list
        articles_response = [
            ArticleInCluster(
                id=a.article_id,
                title=article_map[a.article_id].title if a.article_id in article_map else "",
                summary=article_map[a.article_id].summary if a.article_id in article_map else None,
                source=article_map[a.article_id].source_id if a.article_id in article_map else "",
                published_at=float(article_map[a.article_id].published_at) if a.article_id in article_map and article_map[a.article_id].published_at else None,
                engagement_score=float(article_map[a.article_id].view_count or 0) if a.article_id in article_map else 0.0,
                confidence_score=a.confidence_score,
                preview_image=article_map[a.article_id].preview_image if a.article_id in article_map else None,
                url=article_map[a.article_id].original_url if a.article_id in article_map else "",
            )
            for a in page_assignments
        ]

        # Calculate pagination for articles
        total_articles = cluster.article_count
        total_pages = (total_articles + page_size - 1) // page_size

        pagination = PaginationInfo(
            total_count=total_articles,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        # Calculate average confidence
        avg_confidence = (
            sum(a.confidence_score for a in page_assignments) / len(page_assignments)
            if page_assignments
            else 0.0
        )

        response = ClusterDetail(
            id=cluster.cluster_id,
            label=cluster.label,
            description=cluster.description,
            article_count=cluster.article_count,
            keywords=cluster.keywords or [],
            size_category=cluster.size_category,
            diversity_score=float(cluster.diversity_score),
            confidence=avg_confidence,
            articles=articles_response,
            pagination=pagination,
            metrics=ClusterMetrics(
                silhouette_score=None,
                davies_bouldin_index=None,
                calinski_harabasz_index=None,
            ),
            updated_at=float(cluster.updated_at),
        )

        logger.info(
            f"[CLUSTERS.DETAIL] Returned cluster {cluster_id} with {len(articles_response)} articles"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[CLUSTERS.DETAIL] Error for cluster {cluster_id}: {type(e).__name__}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to get cluster details")


@router.get("/{cluster_id}/articles", response_model=ClusterArticlesResponse)
async def get_cluster_articles(
    cluster_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("date", regex="^(date|engagement|title)$", description="Sort by: date, engagement, or title"),
    cluster_repo: ClusterRepository = Depends(get_cluster_repo),
    article_repo: ArticleRepository = Depends(get_article_repo),
) -> ClusterArticlesResponse:
    """Get paginated articles in a cluster with sorting options.

    Path Parameters:
    - cluster_id: Unique cluster identifier

    Query Parameters:
    - page: Page number (1-indexed, default 1)
    - page_size: Items per page (1-100, default 20)
    - sort: Sort by - "date", "engagement", or "title" (default "date")

    Returns:
    - Paginated article list with pagination metadata
    """
    logger.info(
        f"[CLUSTERS.ARTICLES] Request: cluster_id={cluster_id}, page={page}, page_size={page_size}, sort={sort}"
    )

    try:
        # Verify cluster exists
        cluster = await cluster_repo.get_cluster_metadata(cluster_id)
        if not cluster:
            logger.warning(f"[CLUSTERS.ARTICLES] Cluster not found: {cluster_id}")
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Fetch all articles in cluster (for sorting)
        all_assignments, _ = await cluster_repo.get_articles_in_cluster(
            cluster_id, limit=10000
        )

        # Get article details
        article_ids = [a.article_id for a in all_assignments]
        articles = await cluster_repo.get_articles_by_ids(article_ids) if article_ids else []
        article_map = {a.article_id: a for a in articles}

        # Build full article response list
        articles_full = [
            {
                "assignment": a,
                "article": article_map.get(a.article_id),
                "response": ArticleInCluster(
                    id=a.article_id,
                    title=article_map[a.article_id].title if a.article_id in article_map else "",
                    summary=article_map[a.article_id].summary if a.article_id in article_map else None,
                    source=article_map[a.article_id].source_id if a.article_id in article_map else "",
                    published_at=float(article_map[a.article_id].published_at) if a.article_id in article_map and article_map[a.article_id].published_at else None,
                    engagement_score=float(article_map[a.article_id].view_count or 0) if a.article_id in article_map else 0.0,
                    confidence_score=a.confidence_score,
                    preview_image=article_map[a.article_id].preview_image if a.article_id in article_map else None,
                    url=article_map[a.article_id].original_url if a.article_id in article_map else "",
                )
            }
            for a in all_assignments
            if a.article_id in article_map
        ]

        # Sort based on parameter
        if sort == "engagement":
            articles_full.sort(
                key=lambda x: x["article"].view_count,
                reverse=True
            )
        elif sort == "title":
            articles_full.sort(key=lambda x: x["article"].title)
        else:  # date
            articles_full.sort(
                key=lambda x: x["article"].published_at or 0,
                reverse=True
            )

        # Apply pagination
        total_count = len(articles_full)
        offset = (page - 1) * page_size
        page_items = articles_full[offset : offset + page_size]

        total_pages = (total_count + page_size - 1) // page_size
        if page > total_pages and total_pages > 0:
            raise HTTPException(status_code=400, detail="Page number exceeds total pages")

        pagination = PaginationInfo(
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        response = ClusterArticlesResponse(
            articles=[item["response"] for item in page_items],
            pagination=pagination,
        )

        logger.info(
            f"[CLUSTERS.ARTICLES] Returned {len(response.articles)} articles for cluster {cluster_id}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[CLUSTERS.ARTICLES] Error for cluster {cluster_id}: {type(e).__name__}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to get cluster articles")
