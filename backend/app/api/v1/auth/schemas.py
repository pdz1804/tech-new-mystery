"""Authentication request/response schemas."""

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """User login request."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User information response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    email: str
    is_admin: bool = False
    created_at: str
