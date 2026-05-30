"""FastAPI dependencies for injection."""

from fastapi import Depends, Header

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.utils.pagination import PaginationParams, validate_pagination_limit
from app.repositories.user_repository import UserRepository
from app.repositories.article_repository import ArticleRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.user_saves_repository import UserSavesRepository
from app.repositories.user_preferences_repository import UserPreferencesRepository
from app.repositories.trending_repository import TrendingRepository
from app.services.auth_service import AuthService
from app.services.article_service import ArticleService
from app.services.source_service import SourceService
from app.services.comment_service import CommentService
from app.services.user_service import UserService
from app.services.trending_service import TrendingService
from app.integrations.agent_core_memory import (
    AgentCoreMemory,
    RequestAgentMemory,
    get_agent_memory as create_agent_memory,
)


def get_pagination(
    page: int = 1,
    limit: int = 20,
    last_key: str | None = None,
) -> PaginationParams:
    """Dependency for pagination parameters."""
    limit = validate_pagination_limit(limit)
    return PaginationParams(page=page, limit=limit, last_key=last_key)


async def get_current_user(
    authorization: str | None = Header(None),
) -> dict:
    """Dependency to get and validate current user from JWT token."""
    if not authorization:
        raise UnauthorizedError()

    if not authorization.startswith("Bearer "):
        raise UnauthorizedError()

    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)

    if payload is None:
        raise UnauthorizedError()

    return payload


async def get_optional_user(
    authorization: str | None = Header(None),
) -> dict | None:
    """Dependency to get current user without raising 401 if missing."""
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)

    return payload


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency to ensure user is an admin."""
    if not current_user.get("is_admin", False):
        raise ForbiddenError()
    return current_user


def get_current_user_id(current_user: dict = Depends(get_current_user)) -> str:
    """Dependency to get the current user's ID."""
    user_id = current_user.get("sub")
    if not user_id:
        raise UnauthorizedError()
    return user_id


def get_auth_service() -> AuthService:
    """Dependency to get AuthService."""
    user_repo = UserRepository()
    return AuthService(user_repo=user_repo)


def get_article_service() -> ArticleService:
    """Dependency to get ArticleService."""
    article_repo = ArticleRepository()
    return ArticleService(article_repo=article_repo)


def get_source_service() -> SourceService:
    """Dependency to get SourceService."""
    source_repo = NewsSourceRepository()
    return SourceService(source_repo=source_repo)


def get_comment_service() -> CommentService:
    """Dependency to get CommentService."""
    comment_repo = CommentRepository()
    return CommentService(comment_repo=comment_repo)


def get_user_service() -> UserService:
    """Dependency to get UserService."""
    user_saves_repo = UserSavesRepository()
    user_prefs_repo = UserPreferencesRepository()
    return UserService(user_saves_repo=user_saves_repo, user_prefs_repo=user_prefs_repo)


def get_trending_service() -> TrendingService:
    """Dependency to get TrendingService."""
    trending_repo = TrendingRepository()
    return TrendingService(trending_repo=trending_repo)


async def get_agent_memory() -> AgentCoreMemory:
    """Dependency for per-request Agent Core memory isolation.

    Each request gets its own fresh AgentCoreMemory instance via FastAPI's
    dependency injection system. This prevents state leakage between
    concurrent requests.

    Usage in route handlers:
        @router.post("/chat")
        async def chat_endpoint(memory: AgentCoreMemory = Depends(get_agent_memory)):
            # Each request gets its own isolated memory instance
            await memory.initialize_memory(session_id, user_id)
            ...

    Returns:
        AgentCoreMemory: Fresh instance for this request only
    """
    return create_agent_memory()


async def get_request_agent_memory() -> RequestAgentMemory:
    """Dependency for per-request Agent Memory with cleanup.

    Creates a fresh RequestAgentMemory instance for each request,
    providing request-scoped isolation and automatic cleanup.

    The memory is initialized on demand (lazy initialization) and
    cleaned up automatically after the request completes.

    Usage in route handlers:
        @router.post("/chat")
        async def chat_endpoint(
            req_memory: RequestAgentMemory = Depends(get_request_agent_memory)
        ):
            # req_memory is unique to this request
            await req_memory.initialize(session_id, user_id)
            await req_memory.log_message(session_id, "user", content)
            # Cleanup happens automatically

    Returns:
        RequestAgentMemory: Fresh instance with request scope
    """
    memory = create_agent_memory()
    request_memory = RequestAgentMemory(memory)
    return request_memory
