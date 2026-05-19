"""Tavily Search API client."""

from app.config import settings


class TavilyClient:
    """Client for Tavily Search API."""

    def __init__(self) -> None:
        """Initialize Tavily client."""
        self._api_key = settings.tavily_api_key

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search using Tavily API."""
        raise NotImplementedError
