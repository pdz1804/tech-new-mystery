"""Authentication business logic service."""

import uuid
from app.core.exceptions import DuplicateError, UnauthorizedError, UserNotFoundError
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.repositories.user_repository import UserRepository


class AuthService:
    """Auth service for authentication logic."""

    def __init__(self, user_repo: UserRepository) -> None:
        """Initialize service."""
        self._user_repo = user_repo

    async def register(self, username: str, email: str, password: str) -> dict:
        """Register a new user."""
        username = (username or "").strip()
        if not username:
            raise ValueError("Username cannot be empty")

        # Check if username already exists
        existing = await self._user_repo.get_by_username(username)
        if existing:
            raise DuplicateError(field="username")

        # Create user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)

        user = await self._user_repo.create(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            email=email,
        )

        # Generate tokens
        access_token = create_access_token({"sub": user.user_id, "username": user.username})
        refresh_token = create_refresh_token({"sub": user.user_id})

        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def login(self, username: str, password: str) -> dict:
        """Authenticate user and return tokens."""
        user = await self._user_repo.get_by_username(username)
        if not user:
            raise UnauthorizedError()

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError()

        # Generate tokens
        access_token = create_access_token({"sub": user.user_id, "username": user.username})
        refresh_token = create_refresh_token({"sub": user.user_id})

        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def get_current_user(self, user_id: str) -> dict:
        """Get current user info."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id=user_id)

        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
        }
