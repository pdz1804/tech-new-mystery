"""Anthropic Claude API client."""

from anthropic import Anthropic

from app.config import settings


class ClaudeClient:
    """Client for Claude API."""

    def __init__(self) -> None:
        """Initialize Claude client."""
        self._client = Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def summarize_article(self, content: str) -> str:
        """Summarize article content using Claude."""
        raise NotImplementedError

    async def extract_citations(self, content: str) -> list[str]:
        """Extract citations from content."""
        raise NotImplementedError
