"""News Source business logic service."""

from app.core.exceptions import NotFoundError
from app.repositories.news_source_repository import NewsSourceRepository


class SourceService:
    """Source service for business logic."""

    def __init__(self, source_repo: NewsSourceRepository) -> None:
        """Initialize service."""
        self._source_repo = source_repo

    async def list_sources(self) -> list[dict]:
        """List all news sources sorted by priority."""
        sources = await self._source_repo.list_all()
        sorted_sources = sorted(sources, key=lambda s: s.priority)
        return [
            {
                "source_id": s.source_id,
                "name": s.name,
                "url": s.url,
                "category": s.category,
                "priority": s.priority,
                "enabled": s.enabled,
                "created_at": s.created_at,
            }
            for s in sorted_sources
        ]

    async def get_source(self, source_id: str) -> dict:
        """Get a news source."""
        source = await self._source_repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(resource="source")

        return {
            "source_id": source.source_id,
            "name": source.name,
            "url": source.url,
            "category": source.category,
            "priority": source.priority,
            "enabled": source.enabled,
            "created_at": source.created_at,
        }

    async def create_source(self, source_data: dict) -> dict:
        """Create a news source."""
        source = await self._source_repo.create(source_data)

        return {
            "source_id": source.source_id,
            "name": source.name,
            "url": source.url,
            "category": source.category,
            "priority": source.priority,
            "enabled": source.enabled,
            "created_at": source.created_at,
        }
