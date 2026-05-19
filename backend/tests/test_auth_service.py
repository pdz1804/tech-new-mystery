"""
Comprehensive tests for AuthService.
Tests cover: basic cases, hard cases, complex cases, and edge cases.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.core.exceptions import DuplicateError, UnauthorizedError, UserNotFoundError
from app.core.security import hash_password


@pytest.fixture
def mock_user_repo():
    """Mock UserRepository."""
    repo = AsyncMock(spec=UserRepository)
    return repo


@pytest.fixture
def auth_service(mock_user_repo):
    """Create AuthService with mocked repository."""
    return AuthService(user_repo=mock_user_repo)


class TestAuthServiceRegister:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_basic_success(self, auth_service, mock_user_repo):
        """BASIC: Successfully register a new user."""
        # Mock user doesn't exist yet
        mock_user_repo.get_by_username.return_value = None

        # Mock user creation
        mock_user = MagicMock()
        mock_user.user_id = str(uuid.uuid4())
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.is_admin = False
        mock_user_repo.create.return_value = mock_user

        # Register
        result = await auth_service.register(
            username="testuser",
            email="test@example.com",
            password="SecurePass123",
        )

        # Assertions
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        mock_user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, auth_service, mock_user_repo):
        """EDGE: Attempt to register with existing username."""
        # User already exists
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user_repo.get_by_username.return_value = mock_user

        # Should raise DuplicateError
        with pytest.raises(DuplicateError) as exc_info:
            await auth_service.register(
                username="testuser",
                email="new@example.com",
                password="SecurePass123",
            )

        assert exc_info.value.field == "username"
        mock_user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_empty_username(self, auth_service, mock_user_repo):
        """EDGE: Register with empty username (should fail in schema validation)."""
        mock_user_repo.get_by_username.return_value = None

        # Pydantic validation should catch this, but let's test the service
        with pytest.raises((ValueError, AssertionError)):
            await auth_service.register(
                username="",  # Empty
                email="test@example.com",
                password="SecurePass123",
            )

    @pytest.mark.asyncio
    async def test_register_valid_email_formats(self, auth_service, mock_user_repo):
        """COMPLEX: Register with various valid email formats."""
        mock_user_repo.get_by_username.return_value = None
        mock_user = MagicMock()
        mock_user.user_id = str(uuid.uuid4())
        mock_user.username = "testuser"
        mock_user.is_admin = False
        mock_user_repo.create.return_value = mock_user

        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
        ]

        for email in valid_emails:
            mock_user.email = email
            result = await auth_service.register(
                username="testuser",
                email=email,
                password="SecurePass123",
            )
            assert result["email"] == email

    @pytest.mark.asyncio
    async def test_register_password_hashing(self, auth_service, mock_user_repo):
        """HARD: Verify password is properly hashed (not plaintext)."""
        mock_user_repo.get_by_username.return_value = None
        mock_user = MagicMock()
        mock_user.user_id = str(uuid.uuid4())
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.password_hash = ""
        mock_user_repo.create.return_value = mock_user

        password = "MySecurePassword123!"
        await auth_service.register(
            username="testuser",
            email="test@example.com",
            password=password,
        )

        # Get the password_hash passed to create
        call_args = mock_user_repo.create.call_args
        password_hash = call_args[1]["password_hash"]

        # Verify it's hashed (not plaintext)
        assert password_hash != password
        assert len(password_hash) > len(password)
        assert password_hash.startswith("$pbkdf2-sha256$")  # PBKDF2 hash prefix


class TestAuthServiceLogin:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_login_basic_success(self, auth_service, mock_user_repo):
        """BASIC: Successfully login with correct credentials."""
        password = "CorrectPassword123"
        password_hash = hash_password(password)

        mock_user = MagicMock()
        mock_user.user_id = str(uuid.uuid4())
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.password_hash = password_hash
        mock_user_repo.get_by_username.return_value = mock_user

        result = await auth_service.login(username="testuser", password=password)

        assert result["username"] == "testuser"
        assert "access_token" in result
        assert "refresh_token" in result

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_service, mock_user_repo):
        """EDGE: Login attempt with non-existent user."""
        mock_user_repo.get_by_username.return_value = None

        with pytest.raises(UnauthorizedError):
            await auth_service.login(username="nonexistent", password="password")

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_service, mock_user_repo):
        """BASIC: Login with incorrect password."""
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.password_hash = hash_password("CorrectPassword")
        mock_user_repo.get_by_username.return_value = mock_user

        with pytest.raises(UnauthorizedError):
            await auth_service.login(username="testuser", password="WrongPassword")

    @pytest.mark.asyncio
    async def test_login_case_sensitive_username(self, auth_service, mock_user_repo):
        """COMPLEX: Usernames should be case-sensitive (if stored as-is)."""
        mock_user_repo.get_by_username.return_value = None

        with pytest.raises(UnauthorizedError):
            # Trying to login with different case
            await auth_service.login(username="TestUser", password="password")

        # Verify the exact username was searched
        mock_user_repo.get_by_username.assert_called_with("TestUser")

    @pytest.mark.asyncio
    async def test_login_empty_password(self, auth_service, mock_user_repo):
        """EDGE: Login with empty password."""
        mock_user = MagicMock()
        mock_user.password_hash = hash_password("password")
        mock_user_repo.get_by_username.return_value = mock_user

        with pytest.raises(UnauthorizedError):
            await auth_service.login(username="testuser", password="")

    @pytest.mark.asyncio
    async def test_login_token_generation(self, auth_service, mock_user_repo):
        """HARD: Verify JWT tokens are properly generated."""
        mock_user = MagicMock()
        mock_user.user_id = "user-123"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.password_hash = hash_password("password")
        mock_user_repo.get_by_username.return_value = mock_user

        result = await auth_service.login(username="testuser", password="password")

        access_token = result["access_token"]
        refresh_token = result["refresh_token"]

        # Tokens should be JWT format (3 parts separated by dots)
        assert access_token.count(".") == 2
        assert refresh_token.count(".") == 2
        assert access_token != refresh_token

    @pytest.mark.asyncio
    async def test_login_multiple_attempts(self, auth_service, mock_user_repo):
        """COMPLEX: Multiple sequential login attempts."""
        password = "CorrectPassword"
        password_hash = hash_password(password)
        mock_user = MagicMock()
        mock_user.user_id = str(uuid.uuid4())
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.password_hash = password_hash
        mock_user_repo.get_by_username.return_value = mock_user

        # Attempt 1: Wrong password should fail
        with pytest.raises(UnauthorizedError):
            await auth_service.login(username="testuser", password="WrongPassword")

        # Attempt 2: Correct password should succeed
        result = await auth_service.login(username="testuser", password=password)
        assert "access_token" in result
        assert result["username"] == "testuser"


class TestAuthServiceGetCurrentUser:
    """Tests for getting current user."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, auth_service, mock_user_repo):
        """BASIC: Successfully retrieve current user."""
        user_id = str(uuid.uuid4())
        mock_user = MagicMock()
        mock_user.user_id = user_id
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.is_admin = False
        mock_user.created_at = 1234567890
        mock_user_repo.get_by_id.return_value = mock_user

        result = await auth_service.get_current_user(user_id)

        assert result["user_id"] == user_id
        assert result["username"] == "testuser"
        assert result["is_admin"] is False

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, auth_service, mock_user_repo):
        """EDGE: Get non-existent user."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(UserNotFoundError):
            await auth_service.get_current_user("nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_current_user_admin_flag(self, auth_service, mock_user_repo):
        """COMPLEX: Verify admin flag is returned correctly."""
        user_id = str(uuid.uuid4())

        # Non-admin user
        mock_user = MagicMock()
        mock_user.user_id = user_id
        mock_user.username = "regular"
        mock_user.email = "regular@example.com"
        mock_user.is_admin = False
        mock_user.created_at = 1234567890
        mock_user_repo.get_by_id.return_value = mock_user

        result = await auth_service.get_current_user(user_id)
        assert result["is_admin"] is False

        # Admin user
        mock_user.is_admin = True
        result = await auth_service.get_current_user(user_id)
        assert result["is_admin"] is True

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_id_format(self, auth_service, mock_user_repo):
        """EDGE: Get user with invalid ID format."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(UserNotFoundError):
            await auth_service.get_current_user("")

        with pytest.raises(UserNotFoundError):
            await auth_service.get_current_user("   ")
