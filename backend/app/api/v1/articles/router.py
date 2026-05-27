"""Article endpoints."""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime

logger = logging.getLogger(__name__)

from app.api.dependencies import get_pagination, require_admin, get_current_user, get_current_user_id, get_article_service, get_optional_user
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.api.v1.articles.schemas import (
    ArticleListResponse,
    ArticleDetailResponse,
    CreateArticleRequest,
    UpdateArticleRequest,
    CreateArticleFromUrlRequest,
    DeleteResponse,
    SummarizationResponse,
    PaginationMeta,
)
from app.core.exceptions import ArticleNotFoundError
from app.services.article_service import ArticleService
from app.services.summarization_service import SummarizationService
from app.repositories.article_repository import ArticleRepository
from app.workers.tasks.summary_tasks import summarize_article_task

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/filters")
async def get_filter_metadata():
    """Get filter metadata (category and source counts) for UI filtering."""
    logger.info("[FILTERS] Fetching filter metadata")
    try:
        article_repo = ArticleRepository()
        metadata = await article_repo.get_filter_metadata()
        logger.info(f"[FILTERS] Returned {len(metadata['categories'])} categories and {len(metadata['sources'])} sources")
        return {
            "success": True,
            "data": metadata
        }
    except Exception as e:
        logger.error(f"[FILTERS] Error fetching metadata: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch filter metadata")


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    limit: int = Query(20, ge=1, le=100),
    last_key: str | None = Query(None),
    category: str | None = Query(None, description="Filter by category"),
    source_id: str | None = Query(None, description="Filter by news source"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    sort_by: str = Query("created_at", description="Sort by: created_at, published_at, view_count"),
    service: ArticleService = Depends(get_article_service),
    user: dict | None = Depends(get_optional_user),
) -> ArticleListResponse:
    """List all articles with advanced filtering and pagination."""
    logger.info(f"[LIST_ARTICLES] Request: limit={limit}, category={category}, sort={sort_by}")

    # Build filter params
    filters = {}
    if category:
        filters["category"] = category
    if source_id:
        filters["source_id"] = source_id
    if tags:
        filters["tags"] = tags
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date

    # Validate sort parameter
    valid_sorts = ["created_at", "published_at", "view_count"]
    if sort_by not in valid_sorts:
        sort_by = "created_at"
    filters["sort_by"] = sort_by

    # Apply quality score threshold for non-admin users
    min_quality_score = None
    is_admin = user.get("is_admin", False) if user else False

    if not is_admin:
        try:
            settings_repo = SystemSettingsRepository()
            threshold = await settings_repo.get_threshold()
            min_quality_score = threshold
            logger.debug(f"[LIST_ARTICLES] Non-admin user, applying threshold: {threshold}")
        except Exception as e:
            logger.warning(f"[LIST_ARTICLES] Failed to get threshold: {str(e)}, showing all articles")

    if min_quality_score is not None:
        filters["min_quality_score"] = min_quality_score

    result = await service.list_articles(
        limit=limit,
        last_key=last_key,
        include_content=False,
        **filters,
    )
    logger.info(f"[LIST_ARTICLES] Response: returned {len(result['data'])} articles")

    # Build proper pagination metadata
    has_next = result["meta"]["next_key"] is not None
    pagination_meta = {
        "limit": limit,
        "has_next": has_next,
        "next_cursor": result["meta"]["next_key"] if has_next else None,
    }

    return ArticleListResponse(
        success=True,
        data=result["data"],
        meta=pagination_meta,
    )


@router.get("/{slug}", response_model=ArticleDetailResponse)
async def get_article(
    slug: str,
    service: ArticleService = Depends(get_article_service),
) -> ArticleDetailResponse:
    """Get article by slug."""
    logger.info(f"[GET_ARTICLE] Request: slug={slug}")
    article = await service.get_article_by_slug(slug)
    logger.info(f"[GET_ARTICLE] Found article: id={article['article_id']}, title={article['title']}")

    # Increment view count asynchronously without blocking response
    try:
        # Get article ID from slug to increment view
        article_repo = ArticleRepository()
        article_obj = await article_repo.get_by_slug(slug)
        if article_obj:
            logger.debug(f"[GET_ARTICLE] Incrementing view count for {article_obj.article_id}")
            await service.increment_view_count(article_obj.article_id)
    except Exception as e:
        logger.warning(f"[GET_ARTICLE] Failed to increment view count: {str(e)}")

    return ArticleDetailResponse(success=True, data=article)


@router.post("", response_model=ArticleDetailResponse, status_code=201)
async def create_article(
    payload: CreateArticleRequest,
    _: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service),
) -> ArticleDetailResponse:
    """Create a new article (admin only)."""
    article = await service.create_article(payload.model_dump())
    return ArticleDetailResponse(success=True, data=article)


@router.put("/{slug}", response_model=ArticleDetailResponse, status_code=200)
async def update_article(
    slug: str,
    payload: UpdateArticleRequest,
    _: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service),
) -> ArticleDetailResponse:
    """Update an article by slug (admin only)."""
    try:
        article = await service.update_article(slug, payload.model_dump(exclude_none=True))
        return ArticleDetailResponse(success=True, data=article)
    except ArticleNotFoundError:
        raise HTTPException(status_code=404, detail="Article not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{slug}", response_model=DeleteResponse, status_code=200)
async def delete_article(
    slug: str,
    _: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service),
) -> DeleteResponse:
    """Delete an article by slug (admin only)."""
    deleted = await service.delete_article(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")

    return DeleteResponse(success=True, message="Article deleted successfully")


@router.post("/from-url", response_model=ArticleDetailResponse, status_code=201)
async def create_article_from_url(
    payload: CreateArticleFromUrlRequest,
    _: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service),
) -> ArticleDetailResponse:
    """Create article from URL with intelligent parsing and AI summarization (admin only)."""
    try:
        article = await service.create_from_url(
            str(payload.url),
            title=payload.title,
            author=payload.author,
            auto_summarize=payload.auto_summarize,
        )
        return ArticleDetailResponse(success=True, data=article)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process URL: {str(e)}")


@router.post("/{article_id}/summarize", response_model=SummarizationResponse)
async def summarize_article(
    article_id: str,
    _: dict = Depends(require_admin),
) -> SummarizationResponse:
    """Trigger summarization for an article (admin only)."""
    article_repo = ArticleRepository()
    article = await article_repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Queue the summarization task
    task = summarize_article_task.delay(article_id)

    return SummarizationResponse(
        success=True,
        article_id=article_id,
        status="queued",
        message=f"Summarization task queued with ID: {task.id}",
    )


@router.post("/{article_id}/like")
async def like_article(
    article_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ArticleService = Depends(get_article_service),
):
    """Like an article."""
    try:
        result = await service.like_article(user_id, article_id)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail="Article not found")


@router.delete("/{article_id}/like")
async def unlike_article(
    article_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ArticleService = Depends(get_article_service),
):
    """Unlike an article."""
    try:
        result = await service.unlike_article(user_id, article_id)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail="Article not found")


@router.get("/{article_id}/likes")
async def get_like_count(
    article_id: str,
    service: ArticleService = Depends(get_article_service),
):
    """Get the like count for an article."""
    try:
        result = await service.get_like_count(article_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Article not found")


@router.post("/{article_id}/save")
async def save_article(
    article_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Save an article for later reading."""
    from app.repositories.user_saves_repository import UserSavesRepository
    from app.repositories.article_repository import ArticleRepository

    article_repo = ArticleRepository()
    article = await article_repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    saves_repo = UserSavesRepository()
    try:
        is_saved = await saves_repo.is_saved(user_id, article_id)
        if is_saved:
            raise HTTPException(status_code=400, detail="Article already saved")
        await saves_repo.save_article(user_id, article_id)
        return {"success": True, "message": "Article saved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{article_id}/save")
async def unsave_article(
    article_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Unsave an article."""
    from app.repositories.user_saves_repository import UserSavesRepository

    saves_repo = UserSavesRepository()
    try:
        removed = await saves_repo.unsave_article(user_id, article_id)
        if not removed:
            raise HTTPException(status_code=400, detail="Article not in your saves")
        return {"success": True, "message": "Article removed from saves"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/saved-articles")
async def get_saved_articles(
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100),
    last_key: str | None = Query(None),
):
    """Get all articles saved by the current user with pagination."""
    from app.repositories.user_saves_repository import UserSavesRepository
    from app.repositories.article_repository import ArticleRepository

    saves_repo = UserSavesRepository()
    article_repo = ArticleRepository()

    try:
        saved_items, next_key = await saves_repo.get_user_saves(user_id, limit=limit, last_key=last_key)
        articles = []
        for save in saved_items:
            article = await article_repo.get_by_id(save.article_id)
            if article:
                from app.services.article_service import ArticleService
                service = ArticleService(article_repo)
                articles.append(service._serialize_article(article))

        # Build pagination metadata
        has_next = next_key is not None
        pagination_meta = {
            "limit": limit,
            "has_next": has_next,
            "next_cursor": next_key if has_next else None,
        }

        return {
            "success": True,
            "data": articles,
            "meta": pagination_meta,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
