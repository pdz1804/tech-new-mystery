"""Admin endpoints for search, content management, and user administration."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.api.dependencies import require_admin, get_article_service
from app.services.article_service import ArticleService
from app.services.search_service import SearchService
from app.repositories.article_repository import ArticleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.pending_search_repository import PendingSearchRepository

logger = logging.getLogger(__name__)

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


class UserResponse(BaseModel):
    """User response schema for admin panel."""
    user_id: str
    username: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: str


class UsersListResponse(BaseModel):
    """Response schema for users list endpoint."""
    success: bool
    data: list[UserResponse]
    count: int


class ToggleAdminResponse(BaseModel):
    """Response schema for toggle admin endpoint."""
    success: bool
    data: UserResponse


class PendingArticleResponse(BaseModel):
    """Response schema for pending article."""
    article_id: str
    title: str
    slug: str
    summary: str | None
    category: str | None
    tags: list[str]
    original_url: str
    source_id: str
    created_at: str


class QueueListResponse(BaseModel):
    """Response schema for article queue list."""
    success: bool
    data: list[PendingArticleResponse]
    count: int


class GenericSuccessResponse(BaseModel):
    """Generic success response."""
    success: bool
    message: str


class PendingSearchResponse(BaseModel):
    """Response schema for pending search result."""
    search_id: str
    query: str
    title: str
    url: str
    snippet: str | None
    source: str | None
    created_at: str
    status: str


class SearchesListResponse(BaseModel):
    """Response schema for searches list endpoint."""
    success: bool
    data: list[PendingSearchResponse]
    count: int


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


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    _: dict = Depends(require_admin),
) -> UsersListResponse:
    """List all users with their admin status (admin only)."""
    try:
        user_repo = UserRepository()
        users = await user_repo.list_all(limit=1000)

        user_responses = [
            UserResponse(
                user_id=user.user_id,
                username=user.username,
                email=user.email or "",
                is_admin=user.is_admin,
                is_active=user.is_active,
                created_at=str(user.created_at) if user.created_at else "",
            )
            for user in users
        ]

        logger.info(f"[LIST_USERS] Retrieved {len(user_responses)} users")
        return UsersListResponse(
            success=True,
            data=user_responses,
            count=len(user_responses),
        )

    except Exception as e:
        logger.error(f"[LIST_USERS] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.put("/users/{user_id}/toggle-admin", response_model=ToggleAdminResponse)
async def toggle_admin(
    user_id: str,
    _: dict = Depends(require_admin),
) -> ToggleAdminResponse:
    """Toggle admin status for a user (admin only)."""
    try:
        user_repo = UserRepository()
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Toggle admin status
        new_admin_status = not user.is_admin
        updated_user = await user_repo.update(user_id, is_admin=new_admin_status)

        logger.info(f"[TOGGLE_ADMIN] User {user_id} admin status changed to {new_admin_status}")

        return ToggleAdminResponse(
            success=True,
            data=UserResponse(
                user_id=updated_user.user_id,
                username=updated_user.username,
                email=updated_user.email or "",
                is_admin=updated_user.is_admin,
                is_active=updated_user.is_active,
                created_at=str(updated_user.created_at) if updated_user.created_at else "",
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TOGGLE_ADMIN] Error toggling admin for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle admin: {str(e)}")


@router.get("/articles/queue", response_model=QueueListResponse)
async def list_pending_articles(
    _: dict = Depends(require_admin),
) -> QueueListResponse:
    """List pending (unpublished) articles awaiting approval (admin only)."""
    try:
        article_repo = ArticleRepository()
        pending_articles = await article_repo.list_pending()

        article_responses = [
            PendingArticleResponse(
                article_id=article.article_id,
                title=article.title,
                slug=article.slug,
                summary=article.summary,
                category=article.category,
                tags=article.tags or [],
                original_url=article.original_url,
                source_id=article.source_id,
                created_at=str(article.created_at) if article.created_at else "",
            )
            for article in pending_articles
        ]

        logger.info(f"[QUEUE_LIST] Retrieved {len(article_responses)} pending articles")
        return QueueListResponse(
            success=True,
            data=article_responses,
            count=len(article_responses),
        )

    except Exception as e:
        logger.error(f"[QUEUE_LIST] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list pending articles: {str(e)}")


@router.post("/articles/{article_id}/approve", response_model=GenericSuccessResponse)
async def approve_article(
    article_id: str,
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Approve and publish a pending article (admin only)."""
    try:
        from app.utils.time import now_timestamp

        article_repo = ArticleRepository()
        article = await article_repo.get_by_id(article_id)

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        if article.is_published:
            raise HTTPException(status_code=400, detail="Article is already published")

        # Publish the article
        updated_article = await article_repo.update(
            article_id,
            is_published=True,
            published_at=now_timestamp(),
        )

        logger.info(f"[APPROVE_ARTICLE] Article {article_id} approved and published")

        return GenericSuccessResponse(
            success=True,
            message=f"Article '{updated_article.title}' has been approved and published",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[APPROVE_ARTICLE] Error approving article {article_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to approve article: {str(e)}")


@router.delete("/articles/{article_id}/reject", response_model=GenericSuccessResponse)
async def reject_article(
    article_id: str,
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Reject and delete a pending article (admin only)."""
    try:
        article_repo = ArticleRepository()
        article = await article_repo.get_by_id(article_id)

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Delete the article
        deleted = await article_repo.delete(article_id)

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete article")

        logger.info(f"[REJECT_ARTICLE] Article {article_id} rejected and deleted")

        return GenericSuccessResponse(
            success=True,
            message="Article has been rejected and deleted",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REJECT_ARTICLE] Error rejecting article {article_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reject article: {str(e)}")


@router.get("/searches", response_model=SearchesListResponse)
async def list_pending_searches(
    _: dict = Depends(require_admin),
) -> SearchesListResponse:
    """List pending Tavily search results awaiting approval (admin only)."""
    try:
        from datetime import datetime

        search_repo = PendingSearchRepository()
        pending_searches = await search_repo.list_pending(limit=1000)

        search_responses = [
            PendingSearchResponse(
                search_id=search.search_id,
                query=search.query,
                title=search.title,
                url=search.url,
                snippet=search.snippet,
                source=search.source,
                created_at=datetime.fromtimestamp(search.created_at).isoformat() if search.created_at else "",
                status=search.status,
            )
            for search in pending_searches
        ]

        logger.info(f"[SEARCHES_LIST] Retrieved {len(search_responses)} pending searches")
        return SearchesListResponse(
            success=True,
            data=search_responses,
            count=len(search_responses),
        )

    except Exception as e:
        logger.error(f"[SEARCHES_LIST] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list pending searches: {str(e)}")


@router.post("/searches/{search_id}/approve", response_model=GenericSuccessResponse)
async def approve_search(
    search_id: str,
    _: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service),
) -> GenericSuccessResponse:
    """Approve a pending search result and create an article from it (admin only)."""
    try:
        search_repo = PendingSearchRepository()
        search = await search_repo.get_by_id(search_id)

        if not search:
            raise HTTPException(status_code=404, detail="Search result not found")

        if search.status != "pending":
            raise HTTPException(status_code=400, detail=f"Search is already {search.status}")

        logger.info(f"[APPROVE_SEARCH] Creating article from search: {search.title}")

        # Create article from the search result URL
        article = await service.create_from_url(
            url=search.url,
            title=search.title,
            auto_summarize=True,
        )

        # Mark search as approved
        await search_repo.update_status(search_id, "approved", approved_by="admin")

        logger.info(
            f"[APPROVE_SEARCH] Search {search_id} approved. Article created: {article.get('article_id')}"
        )

        return GenericSuccessResponse(
            success=True,
            message=f"Search approved and article '{article.get('title')}' created successfully",
        )

    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"[APPROVE_SEARCH] Validation error for search {search_id}: {error_msg}")

        # Handle duplicate URL
        if "already exists" in error_msg:
            # Mark search as rejected due to duplicate
            await search_repo.update_status(search_id, "rejected", approved_by="admin")
            raise HTTPException(
                status_code=409,
                detail="Article from this URL already exists in the system"
            )

        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"[APPROVE_SEARCH] Error approving search {search_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to approve search: {str(e)}")


@router.delete("/searches/{search_id}/reject", response_model=GenericSuccessResponse)
async def reject_search(
    search_id: str,
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Reject and delete a pending search result (admin only)."""
    try:
        search_repo = PendingSearchRepository()
        search = await search_repo.get_by_id(search_id)

        if not search:
            raise HTTPException(status_code=404, detail="Search result not found")

        # Delete the search
        deleted = await search_repo.delete(search_id)

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete search")

        logger.info(f"[REJECT_SEARCH] Search {search_id} rejected and deleted")

        return GenericSuccessResponse(
            success=True,
            message="Search result rejected and deleted",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REJECT_SEARCH] Error rejecting search {search_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reject search: {str(e)}")


@router.post("/tavily/trigger", response_model=GenericSuccessResponse)
async def trigger_tavily_scheduler(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Manually trigger Tavily scheduler task (admin only).

    Queues the Tavily scheduler task to fetch articles immediately
    instead of waiting for the next scheduled run (6 hours).
    """
    try:
        from app.workers.tasks.tavily_tasks import tavily_scheduled_task

        logger.info("[TAVILY_TRIGGER] Admin manually triggering Tavily scheduler")

        # Dispatch the task asynchronously
        task = tavily_scheduled_task.delay()

        logger.info(f"[TAVILY_TRIGGER] Task queued with ID: {task.id}")

        return GenericSuccessResponse(
            success=True,
            message=f"Tavily scheduler task triggered successfully. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"[TAVILY_TRIGGER] Error triggering Tavily scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scheduler: {str(e)}")


@router.post("/newsapi/trigger", response_model=GenericSuccessResponse)
async def trigger_newsapi_scheduler(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Manually trigger NewsAPI scheduler task (admin only).

    Queues the NewsAPI scheduler task to fetch articles immediately
    instead of waiting for the next scheduled run (6 hours).
    """
    try:
        from app.workers.tasks.newsapi_tasks import newsapi_scheduled_task

        logger.info("[NEWSAPI_TRIGGER] Admin manually triggering NewsAPI scheduler")

        # Dispatch the task asynchronously
        task = newsapi_scheduled_task.delay()

        logger.info(f"[NEWSAPI_TRIGGER] Task queued with ID: {task.id}")

        return GenericSuccessResponse(
            success=True,
            message=f"NewsAPI scheduler task triggered successfully. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"[NEWSAPI_TRIGGER] Error triggering NewsAPI scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scheduler: {str(e)}")
