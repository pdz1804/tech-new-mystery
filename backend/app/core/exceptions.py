"""Custom application exceptions."""

from dataclasses import dataclass


@dataclass
class AppError(Exception):
    """Base class for all application domain errors."""

    message: str
    code: str


@dataclass
class ArticleNotFoundError(AppError):
    """Raised when an article is not found."""

    article_id: str = ""
    message: str = "Article not found"
    code: str = "ARTICLE_NOT_FOUND"


@dataclass
class UserNotFoundError(AppError):
    """Raised when a user is not found."""

    user_id: str = ""
    message: str = "User not found"
    code: str = "USER_NOT_FOUND"


@dataclass
class UnauthorizedError(AppError):
    """Raised when authentication is required but missing."""

    message: str = "Authentication required"
    code: str = "UNAUTHORIZED"


@dataclass
class ForbiddenError(AppError):
    """Raised when user lacks required permissions."""

    message: str = "Insufficient permissions"
    code: str = "FORBIDDEN"


@dataclass
class DuplicateError(AppError):
    """Raised when a resource already exists."""

    field: str = ""
    message: str = "Resource already exists"
    code: str = "DUPLICATE"

    def __post_init__(self):
        """Generate message based on field if not provided."""
        if self.field and self.message == "Resource already exists":
            self.message = f"A {self.field} with this value already exists"


@dataclass
class ValidationError(AppError):
    """Raised when input validation fails."""

    message: str = "Validation failed"
    code: str = "VALIDATION_ERROR"


@dataclass
class NotFoundError(AppError):
    """Generic not found error."""

    resource: str = ""
    message: str = "Resource not found"
    code: str = "NOT_FOUND"
