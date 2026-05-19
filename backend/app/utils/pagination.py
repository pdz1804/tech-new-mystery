"""Pagination utilities for DynamoDB cursor-based pagination."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PaginationParams:
    """Pagination parameters for DynamoDB queries."""

    page: int = 1
    limit: int = 20
    last_key: str | None = None

    def __post_init__(self) -> None:
        """Validate pagination parameters."""
        if self.limit > 100:
            self.limit = 100
        if self.page < 1:
            self.page = 1


@dataclass
class PaginationMeta:
    """Metadata for paginated responses."""

    page: int
    limit: int
    total: int | None
    last_key: str | None


def validate_pagination_limit(limit: int, max_limit: int = 100) -> int:
    """Validate and constrain a pagination limit."""
    if limit < 1:
        limit = 1
    if limit > max_limit:
        limit = max_limit
    return limit
