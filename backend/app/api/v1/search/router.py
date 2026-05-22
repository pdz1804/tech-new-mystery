"""Search endpoints."""

import logging
import time
from datetime import datetime
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel

from app.repositories.article_repository import ArticleRepository
from app.services.search_service import SearchService
from app.services.qdrant_service import QdrantService
from app.utils.time import timestamp_to_datetime
from app.models.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchResultItem,
    QdrantStatsMetaResponse,
    QdrantStatsResponse,
)
from app.api.dependencies import require_admin

logger = logging.getLogger(__name__)


class ArticleSearchResult(BaseModel):
    """Article search result."""

    article_id: str
    title: str
    slug: str
    summary: str | None
    category: str | None
    tags: list[str]
    published_at: datetime | None
    view_count: int
    created_at: datetime | None = None


class SearchMeta(BaseModel):
    """Search metadata."""

    limit: int
    last_key: str | None = None
    page: int | None = None
    total: int | None = None
    count: int | None = None


class SearchResponse(BaseModel):
    """Search response."""

    success: bool = True
    data: list[ArticleSearchResult]
    meta: SearchMeta


router = APIRouter(prefix="/search", tags=["search"])


def _format_article_model(article) -> dict:
    """Format a DynamoDB article model for search results."""
    return {
        "article_id": article.article_id,
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "category": article.category,
        "tags": getattr(article, "tags", []),
        "published_at": timestamp_to_datetime(article.published_at) if article.published_at else None,
        "view_count": getattr(article, "view_count", 0),
        "created_at": timestamp_to_datetime(article.created_at) if article.created_at else None,
    }


@router.get("", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    tags: list[str] | None = Query(None),
    page: int = Query(1, ge=1),
) -> SearchResponse:
    """Search articles using Qdrant hybrid semantic + keyword search."""
    start_time = time.time()

    logger.info(
        f"[SEARCH] Request: query='{q}', limit={limit}, "
        f"category={category}, tags={tags}, page={page}"
    )

    try:
        # Use Qdrant hybrid search
        qdrant_service = QdrantService()

        logger.debug(f"[SEARCH] Qdrant client available: {qdrant_service.client is not None}")

        if qdrant_service.client is None:
            logger.warning("[SEARCH] Qdrant client unavailable - falling back to SearchService")
            article_repo = ArticleRepository()
            service = SearchService(article_repo)
            result = await service.search(
                query=q,
                limit=limit,
                category=category,
                tags=tags,
            )
            articles = result["results"]
        else:
            # Perform hybrid search via Qdrant
            logger.info("[SEARCH] Starting Qdrant hybrid search...")
            qdrant_results = await qdrant_service.hybrid_search(
                query=q,
                limit=limit * 2,  # Fetch more to apply additional filters
                dense_weight=0.6,
                bm25_weight=0.4,
            )

            logger.info(f"[SEARCH] Qdrant returned {len(qdrant_results)} results")

            # Apply category and tags filters if provided
            filtered_results = qdrant_results

            if category:
                logger.debug(f"[SEARCH] Filtering by category: {category}")
                filtered_results = [
                    r for r in filtered_results
                    if (r.get("category") or "").lower() == category.lower()
                ]
                logger.debug(f"[SEARCH] After category filter: {len(filtered_results)} results")

            if tags:
                logger.debug(f"[SEARCH] Filtering by tags: {tags}")
                # For now, just use first limit results after Qdrant ranking
                # (Qdrant doesn't store tags in payload currently)

            # Hydrate Qdrant hits from DynamoDB so frontend links use the real slug.
            article_repo = ArticleRepository()
            articles = []
            for result in filtered_results[:limit]:
                article = await article_repo.get_by_id(result["article_id"])
                if article:
                    articles.append(_format_article_model(article))
                    continue

                logger.warning(
                    "[SEARCH] Qdrant result points to missing article_id=%s",
                    result.get("article_id"),
                )

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[SEARCH] Response: query='{q}', results={len(articles)}, "
            f"time={elapsed_ms:.0f}ms"
        )

        return SearchResponse(
            success=True,
            data=[
                ArticleSearchResult(
                    article_id=a["article_id"],
                    title=a["title"],
                    slug=a["slug"],
                    summary=a.get("summary"),
                    category=a.get("category"),
                    tags=a.get("tags", []),
                    published_at=a.get("published_at"),
                    view_count=a.get("view_count", 0),
                )
                for a in articles
            ],
            meta=SearchMeta(
                limit=limit,
                last_key=None,
                page=page,
                total=len(articles),
                count=len(articles),
            ),
        )

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[SEARCH] Error: query='{q}', error={str(e)}, "
            f"time={elapsed_ms:.0f}ms",
            exc_info=True
        )

        return SearchResponse(
            success=False,
            data=[],
            meta=SearchMeta(
                limit=limit,
                last_key=None,
                page=page,
                total=0,
                count=0,
            ),
        )


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    payload: HybridSearchRequest,
    _: dict = Depends(require_admin),
) -> HybridSearchResponse:
    """
    Perform hybrid search combining dense semantic and BM25 keyword matching.

    Two-phase approach:
    1. Dense search: Find semantically similar articles using embeddings
    2. BM25 search: Find keyword matches in title and summary
    3. Merge: Combine results with configurable weights

    Query parameters:
    - query: Search query text (required)
    - limit: Max results (1-100, default 10)
    - dense_weight: Weight for dense search (0-1, default 0.6)
    - bm25_weight: Weight for BM25 search (0-1, default 0.4)

    Returns:
    - Ranked results with individual and hybrid scores
    - Query execution time
    """
    logger.info(
        f"[HYBRID_SEARCH] Request: query='{payload.query}', limit={payload.limit}, "
        f"dense_weight={payload.dense_weight}, bm25_weight={payload.bm25_weight}"
    )

    start_time = time.time()

    try:
        qdrant_service = QdrantService()

        # Perform hybrid search
        results = await qdrant_service.hybrid_search(
            query=payload.query,
            limit=payload.limit,
            dense_weight=payload.dense_weight,
            bm25_weight=payload.bm25_weight,
        )

        # Format results
        result_items = [
            SearchResultItem(
                article_id=r["article_id"],
                title=r["title"],
                summary=r["summary"],
                category=r["category"],
                dense_score=r.get("dense_score"),
                bm25_score=r.get("bm25_score"),
                hybrid_score=r.get("hybrid_score"),
            )
            for r in results
        ]

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[HYBRID_SEARCH] Response: query='{payload.query}', results={len(result_items)}, "
            f"time={elapsed_ms:.0f}ms"
        )

        return HybridSearchResponse(
            success=True,
            query=payload.query,
            results=result_items,
            count=len(result_items),
            time_ms=elapsed_ms,
            error=None,
        )

    except Exception as e:
        logger.error(f"[HYBRID_SEARCH] Error: {str(e)}", exc_info=True)
        elapsed_ms = (time.time() - start_time) * 1000

        return HybridSearchResponse(
            success=False,
            query=payload.query,
            results=[],
            count=0,
            time_ms=elapsed_ms,
            error=str(e),
        )


@router.get("/qdrant/stats", response_model=QdrantStatsMetaResponse)
async def get_qdrant_stats(
    _: dict = Depends(require_admin),
) -> QdrantStatsMetaResponse:
    """
    Get Qdrant collection statistics (admin only).

    Returns:
    - Total number of indexed articles
    - Collection status
    - Vector configuration info
    """
    logger.info("[QDRANT_STATS] Fetching collection statistics")

    try:
        qdrant_service = QdrantService()
        stats = await qdrant_service.get_collection_stats()

        if "error" in stats:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=f"Failed to fetch statistics: {stats['error']}"
            )

        logger.info(f"[QDRANT_STATS] Returned: {stats['points_count']} indexed articles")

        return QdrantStatsMetaResponse(
            success=True,
            data=QdrantStatsResponse(**stats),
        )

    except Exception as e:
        logger.error(f"[QDRANT_STATS] Error: {str(e)}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")
