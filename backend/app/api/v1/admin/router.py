"""Admin endpoints for search and content management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import require_admin, get_article_service
from app.services.article_service import ArticleService
from app.services.search_service import SearchService
from app.repositories.article_repository import ArticleRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class TavilySearchRequest(BaseModel):
    """Request schema for Tavily search."""
    query: str
    limit: int = 10


class TavilySearchResponse(BaseModel):
    """Response schema for Tavily search."""
    success: bool
    query: str
    results: list[dict]
    count: int
    error: str | None = None


class ApproveAndCreateRequest(BaseModel):
    """Request schema for approving and creating article from search result."""
    url: str
    query: str
    title: str | None = None
    author: str | None = None


class ArticleData(BaseModel):
    """Article data response schema."""
    article_id: str
    title: str
    slug: str
    summary: str | None
    content: str
    markdown_content: str | None
    author: str | None
    original_url: str
    category: str | None
    tags: list[str]
    is_published: bool


class ApproveAndCreateResponse(BaseModel):
    """Response schema for approve and create endpoint."""
    success: bool
    data: ArticleData | None = None
    error: str | None = None


@router.post("/search/tavily", response_model=TavilySearchResponse)
async def search_tavily(
    payload: TavilySearchRequest,
    _: dict = Depends(require_admin),
) -> TavilySearchResponse:
    """
    Search web using Tavily Search API (admin only).

    Returns tech news and articles from major tech domains.
    """
    search_service = SearchService(ArticleRepository())

    result = await search_service.tavily_search(
        query=payload.query,
        limit=payload.limit,
    )

    return TavilySearchResponse(**result)


@router.post("/search/approve-and-create", response_model=ApproveAndCreateResponse)
async def approve_and_create(
    payload: ApproveAndCreateRequest,
    _: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service),
) -> ApproveAndCreateResponse:
    """
    Approve a search result and create an article from URL (admin only).

    Takes a URL from a Tavily search result and creates an article with
    AI-powered processing for title, summary, category, and tags.
    """
    try:
        # Create article from URL
        article = await service.create_from_url(
            url=payload.url,
            title=payload.title,
            author=payload.author,
            auto_summarize=True,
        )

        return ApproveAndCreateResponse(
            success=True,
            data=ArticleData(**article),
            error=None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create article: {str(e)}")
