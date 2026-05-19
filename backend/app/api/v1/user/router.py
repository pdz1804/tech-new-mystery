"""User endpoints."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_user_service
from app.api.v1.user.schemas import (
    UserPreferencesRequest,
    UserPreferencesResponse,
    SubmissionRequest,
    SubmissionResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/preferences", response_model=dict)
async def get_preferences(
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Get user preferences."""
    prefs = await service.get_user_preferences(current_user["sub"])
    return {"success": True, "data": prefs}


@router.put("/preferences", response_model=dict)
async def update_preferences(
    payload: UserPreferencesRequest,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Update user preferences."""
    prefs = await service.update_user_preferences(current_user["sub"], payload.model_dump())
    return {"success": True, "data": prefs}


@router.get("/saves", response_model=dict)
async def get_saved_articles(
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Get user's saved articles."""
    saves = await service.get_saved_articles(current_user["sub"])
    return {"success": True, "data": saves}


@router.post("/saves/{article_id}", response_model=dict, status_code=201)
async def save_article(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Save an article."""
    save = await service.save_article(current_user["sub"], article_id)
    return {"success": True, "data": save}


@router.delete("/saves/{article_id}", response_model=dict)
async def unsave_article(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Unsave an article."""
    success = await service.unsave_article(current_user["sub"], article_id)
    return {"success": success}
