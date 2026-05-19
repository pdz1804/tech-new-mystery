"""Comments endpoints."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_comment_service
from app.api.v1.comments.schemas import CreateCommentRequest, CommentListResponse
from app.services.comment_service import CommentService

router = APIRouter(tags=["comments"])


@router.get("/articles/{article_id}/comments", response_model=CommentListResponse)
async def get_article_comments(
    article_id: str,
    limit: int = 20,
    service: CommentService = Depends(get_comment_service),
) -> CommentListResponse:
    """Get comments for an article."""
    comments = await service.get_article_comments(article_id, limit=limit)
    return CommentListResponse(success=True, data=comments)


@router.post("/articles/{article_id}/comments", response_model=dict, status_code=201)
async def create_comment(
    article_id: str,
    payload: CreateCommentRequest,
    current_user: dict = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service),
) -> dict:
    """Create a comment on an article."""
    comment = await service.create_comment(
        article_id=article_id,
        user_id=current_user["sub"],
        content=payload.content,
    )
    return {"success": True, "data": comment}


@router.delete("/comments/{comment_id}", response_model=dict)
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service),
) -> dict:
    """Delete a comment (owner only)."""
    success = await service.delete_comment(comment_id)
    return {"success": success}
