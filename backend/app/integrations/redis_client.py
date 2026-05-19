"""Redis cache client."""

import redis

from app.config import settings


class RedisClient:
    """Client for Redis cache."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self._redis = redis.from_url(settings.redis_url)

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        raise NotImplementedError

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache."""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        raise NotImplementedError

    async def get_json(self, key: str) -> dict | None:
        """Get JSON value from cache."""
        raise NotImplementedError

    async def set_json(self, key: str, value: dict, ttl: int = 3600) -> bool:
        """Set JSON value in cache."""
        raise NotImplementedError
