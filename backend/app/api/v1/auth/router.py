"""Authentication endpoints."""

import logging
from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

from app.api.dependencies import get_current_user, get_auth_service
from app.api.v1.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from app.core.exceptions import UserNotFoundError
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register a new user."""
    logger.info(f"[REGISTER] Request: username={payload.username}, email={payload.email}")
    try:
        result = await service.register(
            username=payload.username,
            email=payload.email,
            password=payload.password,
        )
        logger.info(f"[REGISTER] Success: user={payload.username}")
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
        )
    except Exception as e:
        logger.error(f"[REGISTER] Error: {str(e)}")
        raise


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate user and return tokens."""
    logger.info(f"[LOGIN] Request: username={payload.username}")
    try:
        result = await service.login(username=payload.username, password=payload.password)
        logger.info(f"[LOGIN] Success: user={payload.username}, token_type={result['token_type']}")
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
        )
    except Exception as e:
        logger.error(f"[LOGIN] Error: {str(e)}")
        raise


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user."""
    user_id = current_user.get("sub")
    logger.info(f"[GET_ME] Request: user_id={user_id}")
    try:
        user_repo = UserRepository()
        user = await user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"[GET_ME] User not found: user_id={user_id}")
            raise UserNotFoundError(user_id=user_id)

        logger.info(f"[GET_ME] Success: user_id={user.user_id}, username={user.username}, email={user.email}")
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            created_at=str(user.created_at),
        )
    except Exception as e:
        logger.error(f"[GET_ME] Error: {str(e)}", exc_info=True)
        raise
