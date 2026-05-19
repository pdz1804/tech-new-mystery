"""User request/response schemas."""

from pydantic import BaseModel, Field, ConfigDict


class UserPreferencesRequest(BaseModel):
    """User preferences update request."""

    topics: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    notification_enabled: bool = False
    digest_frequency: str = "daily"
    theme: str = "light"


class UserPreferencesResponse(BaseModel):
    """User preferences response."""

    model_config = ConfigDict(from_attributes=True)

    topics: list[str]
    sources: list[str]
    notification_enabled: bool
    digest_frequency: str
    theme: str


class SubmissionRequest(BaseModel):
    """Article submission request."""

    url: str = Field(..., min_length=1)


class SubmissionResponse(BaseModel):
    """Article submission response."""

    model_config = ConfigDict(from_attributes=True)

    submission_id: str
    url: str
    status: str
    submitted_at: str
