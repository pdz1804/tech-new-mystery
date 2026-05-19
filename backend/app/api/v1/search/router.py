"""Search endpoints."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.repositories.article_repository import ArticleRepository
from app.services.search_service import SearchService


class ArticleSearchResult(BaseModel):
    """Article search result."""

    article_id: str
    title: str
    slug: str
    summary: str | None
    category: str | None
    tags: list[str]
    published_at: str | None
    view_count: int
    created_at: str | None = None


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


@router.get("", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    tags: list[str] | None = Query(None),
    page: int = Query(1, ge=1),
) -> SearchResponse:
    """Full-text search articles."""
    article_repo = ArticleRepository()
    service = SearchService(article_repo)

    result = await service.search(
        query=q,
        limit=limit,
        category=category,
        tags=tags,
    )

    articles = result["results"]
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
