"""
Email digest endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.repositories.user_preferences_repository import UserPreferencesRepository
from app.workers.tasks.digest_tasks import send_test_digest
from pydantic import BaseModel

router = APIRouter(prefix="/digest", tags=["digest"])
prefs_repo = UserPreferencesRepository()


class DigestPreferencesSchema(BaseModel):
    email_digest_enabled: bool
    email_digest_frequency: str = "daily"  # "daily" or "weekly"

    class Config:
        json_schema_extra = {
            "example": {
                "email_digest_enabled": True,
                "email_digest_frequency": "daily",
            }
        }


@router.get("/preferences")
async def get_digest_preferences(user: dict = Depends(get_current_user)):
    """Get current user's email digest preferences."""
    try:
        prefs = prefs_repo.get_user_preferences(user["user_id"])
        if not prefs:
            return {
                "email_digest_enabled": False,
                "email_digest_frequency": "daily",
            }

        return {
            "email_digest_enabled": prefs.get("email_digest_enabled", False),
            "email_digest_frequency": prefs.get("email_digest_frequency", "daily"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching preferences: {str(e)}",
        )


@router.put("/preferences")
async def update_digest_preferences(
    prefs: DigestPreferencesSchema,
    user: dict = Depends(get_current_user),
):
    """Update email digest preferences for current user."""
    try:
        # Validate frequency
        if prefs.email_digest_frequency not in ["daily", "weekly"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Digest frequency must be 'daily' or 'weekly'",
            )

        # Update preferences
        prefs_repo.update_user_preferences(
            user["user_id"],
            {
                "email_digest_enabled": prefs.email_digest_enabled,
                "email_digest_frequency": prefs.email_digest_frequency,
            },
        )

        return {
            "success": True,
            "message": "Email digest preferences updated",
            "email_digest_enabled": prefs.email_digest_enabled,
            "email_digest_frequency": prefs.email_digest_frequency,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating preferences: {str(e)}",
        )


@router.post("/test-digest")
async def send_test_email_digest(user: dict = Depends(get_current_user)):
    """Send a test digest email to the current user."""
    try:
        # Send test digest asynchronously
        result = send_test_digest.delay(
            user_email=user.get("email"),
            user_name=user.get("username"),
        )

        return {
            "success": True,
            "message": "Test digest email is being sent",
            "task_id": result.id if hasattr(result, "id") else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending test digest: {str(e)}",
        )
