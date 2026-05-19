"""Trending articles endpoints."""

from fastapi import APIRouter, Query, Depends

from app.api.dependencies import get_trending_service
from app.services.trending_service import TrendingService

router = APIRouter(prefix="/trending", tags=["trending"])


@router.get("")
async def get_trending(
    limit: int = Query(20, ge=1, le=100),
    service: TrendingService = Depends(get_trending_service),
):
    """Get trending articles."""
    articles = await service.get_trending_articles(limit=limit)
    return {
        "success": True,
        "data": articles,
        "meta": {"limit": limit, "count": len(articles)},
    }
