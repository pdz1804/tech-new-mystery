"""Authentication and session validation for chat endpoints."""

import logging
from fastapi import Depends, HTTPException, Header, status

from app.core.security import decode_access_token
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)


async def get_chat_auth_user(
    authorization: str | None = Header(None),
) -> dict:
    """
    Validate JWT token from Authorization header.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        Decoded token payload with user_id in 'sub' field

    Raises:
        UnauthorizedError: If token is missing, invalid, or expired
    """
    if not authorization:
        logger.warning("[CHAT_AUTH] Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        logger.warning("[CHAT_AUTH] Invalid authorization header format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)

    if payload is None:
        logger.warning("[CHAT_AUTH] Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        logger.warning("[CHAT_AUTH] Token missing user_id (sub)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"[CHAT_AUTH] Authenticated user: {user_id}")
    return payload


async def validate_session_ownership(
    session_id: str,
    current_user: dict | None = Depends(get_chat_auth_user),
    chat_service: ChatService = Depends(),
    user_id: str | None = None,
) -> dict:
    """
    Validate that a session exists and belongs to the current user.

    Args:
        session_id: Session ID to validate
        current_user: Current authenticated user
        chat_service: Chat service instance
        user_id: Optional explicit user ID for direct unit tests

    Returns:
        Session data if validation passes

    Raises:
        HTTPException: 404 if session not found, 403 if user doesn't own it
    """
    if isinstance(current_user, dict):
        user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"[SESSION_VALIDATION] Validating session {session_id} for user {user_id}")

    session = await chat_service.get_session(session_id, user_id)

    if not session:
        logger.warning(f"[SESSION_VALIDATION] Session not found: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Verify ownership (get_session already checks user_id, but double-check)
    if session.get("user_id") != user_id:
        logger.warning(
            f"[SESSION_VALIDATION] User {user_id} attempted to access session {session_id} "
            f"owned by {session.get('user_id')}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this session",
        )

    # Verify session is active
    if not session.get("is_active", False):
        logger.warning(f"[SESSION_VALIDATION] Session {session_id} is not active")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session is archived or inactive",
        )

    logger.debug(f"[SESSION_VALIDATION] Session validation passed: {session_id}")
    return session
