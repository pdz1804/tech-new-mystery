"""Chat endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.api.dependencies import get_current_user
from app.api.v1.chat.schemas import (
    CreateSessionRequest,
    SessionResponse,
    MessageRequest,
    MessageResponse,
    SessionListResponse,
    MessageListResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=dict, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create a new chat session.

    Args:
        payload: Session creation request
        current_user: Current authenticated user

    Returns:
        Created session object
    """
    service = ChatService()
    session = await service.create_session(
        user_id=current_user["sub"],
        title=payload.title,
        description=payload.description,
    )
    return {"success": True, "data": session}


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SessionListResponse:
    """List user's chat sessions (sorted by recency).

    Args:
        current_user: Current authenticated user
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        List of sessions with pagination metadata
    """
    service = ChatService()
    result = await service.list_sessions(
        user_id=current_user["sub"],
        page=page,
        page_size=page_size,
    )
    return SessionListResponse(
        success=True,
        data=[SessionResponse(**s) for s in result["sessions"]],
        meta={
            "page": result["page"],
            "limit": result["page_size"],
            "total": result["total"],
            "last_key": None,
        },
    )


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get session details (session owner only).

    Args:
        session_id: Session ID
        current_user: Current authenticated user

    Returns:
        Session object

    Raises:
        404: Session not found
        403: User doesn't own this session
    """
    service = ChatService()
    session = await service.get_session(session_id, current_user["sub"])
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return {"success": True, "data": session}


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> MessageListResponse:
    """Get session message history with pagination (session owner only).

    Args:
        session_id: Session ID
        current_user: Current authenticated user
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        List of messages with pagination metadata

    Raises:
        404: Session not found
        403: User doesn't own this session
    """
    service = ChatService()
    try:
        result = await service.get_messages(
            session_id=session_id,
            user_id=current_user["sub"],
            page=page,
            page_size=page_size,
        )
        return MessageListResponse(
            success=True,
            data=[MessageResponse(**m) for m in result["messages"]],
            meta={
                "page": result["page"],
                "limit": result["page_size"],
                "total": result["total"],
                "last_key": None,
            },
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this session",
        )


@router.post("/sessions/{session_id}/message", response_model=dict, status_code=201)
async def add_message(
    session_id: str,
    payload: MessageRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Add a user message to a chat session.

    Args:
        session_id: Session ID
        payload: Message request with user content
        current_user: Current authenticated user

    Returns:
        Created message object

    Raises:
        404: Session not found
        403: User doesn't own this session
    """
    service = ChatService()
    try:
        message = await service.add_message(
            session_id=session_id,
            user_id=current_user["sub"],
            role="user",
            content=payload.content,
        )
        return {"success": True, "data": message}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this session",
        )
