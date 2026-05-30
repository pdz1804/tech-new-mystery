"""Comprehensive tests for chat auth and session validation."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from jose import jwt
from datetime import datetime, timedelta

from app.api.v1.chat.auth import get_chat_auth_user, validate_session_ownership
from app.core.security import create_access_token
from app.core.exceptions import UnauthorizedError
from app.config import settings
from app.services.chat_service import ChatService


@pytest.fixture
def valid_user_id():
    """Valid user ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def other_user_id():
    """Different user ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def valid_session_id():
    """Valid session ID for testing."""
    return f"sess-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def valid_access_token(valid_user_id):
    """Create a valid JWT access token."""
    return create_access_token({
        "sub": valid_user_id,
        "username": "testuser",
        "is_admin": False
    })


@pytest.fixture
def expired_access_token(valid_user_id):
    """Create an expired JWT access token."""
    to_encode = {
        "sub": valid_user_id,
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


@pytest.fixture
def invalid_token():
    """Invalid JWT token."""
    return "invalid.token.here"


@pytest.fixture
def mock_chat_service():
    """Create mock ChatService."""
    return AsyncMock(spec=ChatService)


@pytest.fixture
def active_session(valid_user_id, valid_session_id):
    """Create an active session dict."""
    return {
        "session_id": valid_session_id,
        "user_id": valid_user_id,
        "title": "Test Session",
        "description": "Test description",
        "created_at": 1000.0,
        "updated_at": 1000.0,
        "last_message_at": 1000.0,
        "message_count": 0,
        "is_active": True,
    }


# ============================================================================
# TOKEN VALIDATION TESTS
# ============================================================================

class TestChatAuthTokenValidation:
    """Test JWT token validation in get_chat_auth_user."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """BASIC: Missing authorization header should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization=None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authorization header required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_authorization_format(self):
        """BASIC: Invalid authorization format should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization="NotBearer token123")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authorization header format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """BASIC: Invalid token should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization="Bearer invalid.token.here")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_expired_token(self, expired_access_token):
        """EDGE: Expired token should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization=f"Bearer {expired_access_token}")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_token(self, valid_access_token, valid_user_id):
        """BASIC: Valid token should return payload with user_id."""
        payload = await get_chat_auth_user(authorization=f"Bearer {valid_access_token}")

        assert payload is not None
        assert payload["sub"] == valid_user_id
        assert "username" in payload

    @pytest.mark.asyncio
    async def test_token_missing_user_id(self):
        """EDGE: Token without 'sub' should raise 401."""
        # Create token without user_id
        bad_token = jwt.encode(
            {
                "username": "testuser",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization=f"Bearer {bad_token}")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_bearer_case_insensitive(self, valid_access_token):
        """EDGE: Bearer prefix case should be case-sensitive (spec compliant)."""
        # FastAPI requires exact "Bearer " prefix
        with pytest.raises(HTTPException):
            await get_chat_auth_user(authorization=f"bearer {valid_access_token}")

    @pytest.mark.asyncio
    async def test_empty_bearer_token(self):
        """EDGE: Empty token after Bearer should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization="Bearer ")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# SESSION VALIDATION TESTS
# ============================================================================

class TestSessionValidation:
    """Test session ownership and existence validation."""

    @pytest.mark.asyncio
    async def test_session_not_found(
        self,
        valid_user_id,
        valid_session_id,
        mock_chat_service,
    ):
        """BASIC: Non-existent session should raise 404."""
        mock_chat_service.get_session.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=valid_user_id,
                chat_service=mock_chat_service,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Session not found" in exc_info.value.detail
        mock_chat_service.get_session.assert_called_once_with(valid_session_id, valid_user_id)

    @pytest.mark.asyncio
    async def test_valid_session_ownership(
        self,
        valid_user_id,
        valid_session_id,
        active_session,
        mock_chat_service,
    ):
        """BASIC: Valid session ownership should succeed."""
        mock_chat_service.get_session.return_value = active_session

        session = await validate_session_ownership(
            session_id=valid_session_id,
            user_id=valid_user_id,
            chat_service=mock_chat_service,
        )

        assert session == active_session
        assert session["session_id"] == valid_session_id
        assert session["user_id"] == valid_user_id

    @pytest.mark.asyncio
    async def test_wrong_user_ownership(
        self,
        valid_user_id,
        other_user_id,
        valid_session_id,
        mock_chat_service,
    ):
        """HARD: Wrong user ownership should raise 403."""
        # Session belongs to valid_user_id, but other_user_id tries to access
        session_owned_by_other = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "title": "Other's Session",
            "is_active": True,
        }
        mock_chat_service.get_session.return_value = session_owned_by_other

        # Call with different user_id
        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=other_user_id,
                chat_service=mock_chat_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_inactive_session(
        self,
        valid_user_id,
        valid_session_id,
        mock_chat_service,
    ):
        """HARD: Inactive session should raise 403."""
        inactive_session = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "title": "Archived Session",
            "is_active": False,
        }
        mock_chat_service.get_session.return_value = inactive_session

        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=valid_user_id,
                chat_service=mock_chat_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "archived or inactive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_session_without_is_active_field(
        self,
        valid_user_id,
        valid_session_id,
        mock_chat_service,
    ):
        """EDGE: Session missing is_active field should fail validation."""
        session_without_flag = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "title": "Test Session",
            # Missing 'is_active' field
        }
        mock_chat_service.get_session.return_value = session_without_flag

        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=valid_user_id,
                chat_service=mock_chat_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestChatAuthIntegration:
    """Integration tests with real tokens and session validation."""

    @pytest.mark.asyncio
    async def test_full_auth_flow_success(
        self,
        valid_user_id,
        valid_session_id,
        valid_access_token,
        active_session,
        mock_chat_service,
    ):
        """HARD: Full auth flow should succeed end-to-end."""
        # Step 1: Validate token
        payload = await get_chat_auth_user(
            authorization=f"Bearer {valid_access_token}"
        )
        assert payload["sub"] == valid_user_id

        # Step 2: Validate session
        mock_chat_service.get_session.return_value = active_session
        session = await validate_session_ownership(
            session_id=valid_session_id,
            user_id=payload["sub"],
            chat_service=mock_chat_service,
        )
        assert session["session_id"] == valid_session_id

    @pytest.mark.asyncio
    async def test_auth_fails_on_invalid_token(
        self,
        valid_user_id,
        valid_session_id,
        active_session,
        mock_chat_service,
    ):
        """HARD: Auth should fail on invalid token before session validation."""
        # Step 1: Token validation fails
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization="Bearer invalid.token")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

        # Step 2: Session validation never called
        mock_chat_service.get_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_validation_fails_after_auth(
        self,
        valid_user_id,
        valid_session_id,
        other_user_id,
        valid_access_token,
        mock_chat_service,
    ):
        """HARD: Auth passes but session validation fails."""
        # Step 1: Token validation succeeds
        payload = await get_chat_auth_user(
            authorization=f"Bearer {valid_access_token}"
        )
        assert payload["sub"] == valid_user_id

        # Step 2: Session validation fails (different owner)
        other_users_session = {
            "session_id": valid_session_id,
            "user_id": other_user_id,
            "title": "Other User's Session",
            "is_active": True,
        }
        mock_chat_service.get_session.return_value = other_users_session

        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=valid_user_id,
                chat_service=mock_chat_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# ERROR CODE TESTS
# ============================================================================

class TestErrorCodes:
    """Verify correct HTTP status codes for all error scenarios."""

    @pytest.mark.asyncio
    async def test_no_token_returns_401(self):
        """Should return 401 for missing token."""
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        """Should return 401 for invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            await get_chat_auth_user(authorization="Bearer bad")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_session_not_found_returns_404(
        self,
        valid_user_id,
        valid_session_id,
        mock_chat_service,
    ):
        """Should return 404 when session doesn't exist."""
        mock_chat_service.get_session.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=valid_user_id,
                chat_service=mock_chat_service,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_owner_returns_403(
        self,
        valid_user_id,
        other_user_id,
        valid_session_id,
        mock_chat_service,
    ):
        """Should return 403 when user doesn't own session."""
        session = {
            "session_id": valid_session_id,
            "user_id": other_user_id,
            "is_active": True,
        }
        mock_chat_service.get_session.return_value = session
        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=valid_user_id,
                chat_service=mock_chat_service,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_inactive_session_returns_403(
        self,
        valid_user_id,
        valid_session_id,
        mock_chat_service,
    ):
        """Should return 403 for archived sessions."""
        session = {
            "session_id": valid_session_id,
            "user_id": valid_user_id,
            "is_active": False,
        }
        mock_chat_service.get_session.return_value = session
        with pytest.raises(HTTPException) as exc_info:
            await validate_session_ownership(
                session_id=valid_session_id,
                user_id=valid_user_id,
                chat_service=mock_chat_service,
            )
        assert exc_info.value.status_code == 403
