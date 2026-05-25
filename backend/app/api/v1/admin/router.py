"""Admin endpoints for search, content management, and user administration."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
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
    total: int = 0
    page: int = 1
    total_pages: int = 1


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
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: dict = Depends(require_admin),
) -> SearchesListResponse:
    """List pending Tavily search results awaiting approval (admin only) with pagination."""
    try:
        from datetime import datetime

        search_repo = PendingSearchRepository()
        all_pending = await search_repo.list_pending(limit=1000)

        total = len(all_pending)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_items = all_pending[start_idx:end_idx]

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
            for search in page_items
        ]

        logger.info(f"[SEARCHES_LIST] Retrieved page {page}/{total_pages}, {len(search_responses)} items")
        return SearchesListResponse(
            success=True,
            data=search_responses,
            count=len(search_responses),
            total=total,
            page=page,
            total_pages=total_pages,
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
        error_msg = str(e)
        logger.error(f"[APPROVE_SEARCH] Error approving search {search_id}: {error_msg}")

        # Handle scraping failures gracefully
        if "scraping" in error_msg.lower() or "crawl" in error_msg.lower() or "blocked" in error_msg.lower():
            # Auto-reject search if scraping failed (likely paywall or bot protection)
            await search_repo.update_status(search_id, "rejected", approved_by="system")
            raise HTTPException(
                status_code=422,
                detail=f"Unable to scrape this URL. {error_msg}. Search marked as rejected."
            )

        raise HTTPException(status_code=500, detail=f"Failed to approve search: {error_msg}")


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
    start_date: str | None = None,
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Manually trigger Tavily scheduler task (admin only).

    Queues the Tavily scheduler task to fetch articles immediately
    instead of waiting for the next scheduled run (6 hours).

    Args:
        start_date: Optional ISO format date (YYYY-MM-DD) to search from.
                    If not provided, defaults to yesterday.
    """
    try:
        from app.workers.tasks.tavily_tasks import tavily_scheduled_task
        from datetime import datetime, timedelta

        logger.info("[TAVILY_TRIGGER] Admin manually triggering Tavily scheduler")
        if start_date:
            logger.info(f"[TAVILY_TRIGGER] Using custom date: {start_date}")
        else:
            start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"[TAVILY_TRIGGER] Using yesterday's date: {start_date}")

        # Dispatch the task asynchronously with the date parameter
        task = tavily_scheduled_task.delay(start_date=start_date)

        logger.info(f"[TAVILY_TRIGGER] Task queued with ID: {task.id}")

        return GenericSuccessResponse(
            success=True,
            message=f"Tavily scheduler task triggered successfully. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"[TAVILY_TRIGGER] Error triggering Tavily scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scheduler: {str(e)}")


class NewsAPITriggerRequest(BaseModel):
    """Request schema for NewsAPI trigger."""
    query: str | None = None
    from_date: str | None = None


@router.post("/newsapi/trigger", response_model=GenericSuccessResponse)
async def trigger_newsapi_scheduler(
    request: NewsAPITriggerRequest,
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Manually trigger NewsAPI scheduler task (admin only).

    Queues the NewsAPI scheduler task to fetch articles immediately
    instead of waiting for the next scheduled run (6 hours).

    Args:
        query: Optional custom search query. If not provided, uses default.
        from_date: Optional ISO format date (YYYY-MM-DD) to search from.
                   If not provided, defaults to yesterday.
    """
    try:
        from app.workers.tasks.newsapi_tasks import newsapi_scheduled_task
        from datetime import datetime, timedelta

        logger.info("[NEWSAPI_TRIGGER] Admin manually triggering NewsAPI scheduler")

        from_date = request.from_date
        query = request.query

        if from_date:
            logger.info(f"[NEWSAPI_TRIGGER] Using custom date: {from_date}")
        else:
            from_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"[NEWSAPI_TRIGGER] Using yesterday's date: {from_date}")

        if query:
            logger.info(f"[NEWSAPI_TRIGGER] Using custom query: {query}")
        else:
            logger.info("[NEWSAPI_TRIGGER] Using default query")

        # Dispatch the task asynchronously with both parameters
        task = newsapi_scheduled_task.delay(from_date=from_date, query=query)

        logger.info(f"[NEWSAPI_TRIGGER] Task queued with ID: {task.id}")

        return GenericSuccessResponse(
            success=True,
            message=f"NewsAPI scheduler task triggered successfully. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"[NEWSAPI_TRIGGER] Error triggering NewsAPI scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scheduler: {str(e)}")


@router.delete("/searches/clean", response_model=GenericSuccessResponse)
async def clean_searches_queue(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Delete all pending searches from the queue (admin only).

    WARNING: This will permanently delete all pending search results awaiting approval.
    Use with caution.
    """
    try:
        logger.warning("[CLEAN_SEARCHES] Admin initiating queue cleanup")

        search_repo = PendingSearchRepository()
        pending_searches = await search_repo.list_pending(limit=1000)

        if not pending_searches:
            return GenericSuccessResponse(
                success=True,
                message="Queue is already empty - nothing to clean",
            )

        count = 0
        for search in pending_searches:
            try:
                await search_repo.delete(search.search_id)
                count += 1
            except Exception as e:
                logger.error(f"[CLEAN_SEARCHES] Error deleting search {search.search_id}: {str(e)}")
                continue

        logger.warning(f"[CLEAN_SEARCHES] Successfully deleted {count} pending searches")

        return GenericSuccessResponse(
            success=True,
            message=f"Successfully cleaned {count} pending searches from the queue",
        )

    except Exception as e:
        logger.error(f"[CLEAN_SEARCHES] Error cleaning searches: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clean queue: {str(e)}")


@router.post("/qdrant/backfill", response_model=GenericSuccessResponse)
async def trigger_qdrant_backfill(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Manually trigger Qdrant backfill task to index all articles (admin only).

    This will:
    1. Fetch all articles from DynamoDB
    2. Skip already-indexed articles
    3. Generate embeddings and index into Qdrant
    4. Report progress and final statistics

    Warning: This is computationally expensive and may take several minutes.
    """
    try:
        import asyncio
        from app.repositories.article_repository import ArticleRepository
        from app.services.qdrant_service import QdrantService

        logger.warning("[QDRANT_BACKFILL] Admin manually triggering Qdrant backfill")

        # Run backfill in background (don't block response)
        asyncio.create_task(_backfill_qdrant_task())

        return GenericSuccessResponse(
            success=True,
            message="Qdrant backfill task started in background. Monitor logs for progress.",
        )

    except Exception as e:
        logger.error(f"[QDRANT_BACKFILL] Error triggering backfill: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger backfill: {str(e)}")


async def _backfill_qdrant_task():
    """Background task for Qdrant backfill."""
    try:
        import time
        from app.repositories.article_repository import ArticleRepository
        from app.services.qdrant_service import QdrantService

        logger.info("[QDRANT_BACKFILL] Starting background backfill task")
        start_time = time.time()

        # Initialize services
        article_repo = ArticleRepository()
        qdrant_service = QdrantService()

        # Fetch all articles
        articles, _ = await article_repo.list_all(limit=10000)

        if not articles:
            logger.warning("[QDRANT_BACKFILL] No articles found")
            return

        total = len(articles)
        logger.info(f"[QDRANT_BACKFILL] Found {total} articles to process")

        # Process articles
        batch_size = 10
        indexed_count = 0
        skipped_count = 0
        failed_count = 0

        for batch_num in range(0, total, batch_size):
            batch = articles[batch_num : batch_num + batch_size]

            for article in batch:
                try:
                    # Check if already indexed
                    exists = await qdrant_service.article_exists(article.article_id)
                    if exists:
                        skipped_count += 1
                        continue

                    # Index article
                    success = await qdrant_service.index_article(
                        article_id=article.article_id,
                        slug=article.slug,
                        title=article.title,
                        summary=article.summary,
                        content=article.content,
                        category=article.category,
                        author=article.author,
                        published_at=article.published_at,
                        view_count=article.view_count,
                        source_id=article.source_id,
                    )

                    if success:
                        indexed_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    failed_count += 1
                    logger.warning(f"[QDRANT_BACKFILL] Error indexing {article.article_id}: {str(e)}")

        elapsed_time = time.time() - start_time
        logger.info(
            f"[QDRANT_BACKFILL] Completed: indexed={indexed_count}, "
            f"skipped={skipped_count}, failed={failed_count}, time={elapsed_time:.1f}s"
        )

    except Exception as e:
        logger.error(f"[QDRANT_BACKFILL] Task failed: {str(e)}", exc_info=True)


@router.get("/qdrant/stats", response_model=GenericSuccessResponse)
async def get_qdrant_stats(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Get Qdrant collection statistics (admin only)."""
    try:
        from app.services.qdrant_service import QdrantService

        logger.info("[QDRANT_STATS] Fetching collection statistics")
        qdrant_service = QdrantService()
        stats = await qdrant_service.get_collection_stats()

        if "error" in stats:
            raise HTTPException(status_code=503, detail=f"Failed to fetch statistics: {stats['error']}")

        logger.info(f"[QDRANT_STATS] Collection has {stats['points_count']} indexed articles")

        return GenericSuccessResponse(
            success=True,
            message=f"Collection: {stats['collection_name']}, "
                    f"Articles indexed: {stats['points_count']}, "
                    f"Status: {stats['status']}"
        )

    except Exception as e:
        logger.error(f"[QDRANT_STATS] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")


# ============================================================
# NEW: Auto-Review, Threshold Settings, Backfill
# ============================================================


class ThresholdResponse(BaseModel):
    """Response for threshold get/set endpoints."""
    success: bool
    threshold: float


class UpdateThresholdRequest(BaseModel):
    """Request to update quality score threshold."""
    threshold: float = Field(..., ge=0.0, le=10.0)


@router.post("/searches/auto-review", response_model=GenericSuccessResponse)
async def trigger_auto_review(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Trigger auto-review of all pending searches (admin only).

    Dispatches worker tasks to evaluate and approve/reject each pending search.
    """
    try:
        from app.workers.tasks.evaluation_tasks import auto_review_queue_task

        logger.info("[AUTO_REVIEW] Admin triggered auto-review of queue")
        task = auto_review_queue_task.delay()

        return GenericSuccessResponse(
            success=True,
            message=f"Auto-review task queued. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"[AUTO_REVIEW] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger auto-review: {str(e)}")


@router.get("/settings/threshold", response_model=ThresholdResponse)
async def get_threshold(
    _: dict = Depends(require_admin),
) -> ThresholdResponse:
    """Get current quality score threshold (admin only)."""
    try:
        from app.repositories.system_settings_repository import SystemSettingsRepository

        repo = SystemSettingsRepository()
        threshold = await repo.get_threshold()

        logger.info(f"[GET_THRESHOLD] Retrieved threshold: {threshold}")
        return ThresholdResponse(success=True, threshold=threshold)
    except Exception as e:
        logger.error(f"[GET_THRESHOLD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get threshold: {str(e)}")


@router.put("/settings/threshold", response_model=ThresholdResponse)
async def update_threshold(
    payload: UpdateThresholdRequest,
    _: dict = Depends(require_admin),
) -> ThresholdResponse:
    """Update quality score threshold (admin only).

    Args:
        threshold: New threshold value (0.0 to 10.0)
    """
    try:
        from app.repositories.system_settings_repository import SystemSettingsRepository

        repo = SystemSettingsRepository()
        new_threshold = await repo.set_threshold(payload.threshold)

        logger.info(f"[UPDATE_THRESHOLD] Changed threshold to: {new_threshold}")
        return ThresholdResponse(success=True, threshold=new_threshold)
    except Exception as e:
        logger.error(f"[UPDATE_THRESHOLD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update threshold: {str(e)}")


@router.post("/articles/backfill-scores", response_model=GenericSuccessResponse)
async def trigger_score_backfill(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Trigger backfill of quality scores for existing articles (admin only).

    Finds articles without quality_score and dispatches evaluation tasks.
    """
    try:
        from app.workers.tasks.evaluation_tasks import backfill_quality_scores_task

        logger.warning("[BACKFILL_SCORES] Admin triggered backfill task")
        task = backfill_quality_scores_task.delay()

        return GenericSuccessResponse(
            success=True,
            message=f"Backfill task queued. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"[BACKFILL_SCORES] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger backfill: {str(e)}")


@router.post("/articles/backfill-scores-force", response_model=GenericSuccessResponse)
async def trigger_force_score_backfill(
    _: dict = Depends(require_admin),
) -> GenericSuccessResponse:
    """Force backfill of quality scores for ALL articles (admin only).

    Re-evaluates all articles regardless of existing quality_score.
    """
    try:
        from app.workers.tasks.evaluation_tasks import backfill_quality_scores_force_task

        logger.warning("[BACKFILL_SCORES_FORCE] Admin triggered force backfill task")
        task = backfill_quality_scores_force_task.delay()

        return GenericSuccessResponse(
            success=True,
            message=f"Force backfill task queued. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"[BACKFILL_SCORES_FORCE] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger force backfill: {str(e)}")
