"""Hybrid search endpoint combining dense embeddings and BM25 keyword matching."""

import logging
import time
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_admin
from app.models.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchResultItem,
    QdrantStatsMetaResponse,
    QdrantStatsResponse,
)
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


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
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")
