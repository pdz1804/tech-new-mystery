"""News Source data repository."""

import asyncio
import uuid
from pynamodb.exceptions import DoesNotExist

from app.models.news_source import NewsSourceModel
from app.utils.time import now_timestamp


class NewsSourceRepository:
    """News source repository for DynamoDB access."""

    async def get_by_id(self, source_id: str) -> NewsSourceModel | None:
        """Get source by ID."""
        try:
            return await asyncio.to_thread(NewsSourceModel.get, source_id)
        except DoesNotExist:
            return None

    async def list_all(self) -> list[NewsSourceModel]:
        """List all sources."""
        results = await asyncio.to_thread(lambda: list(NewsSourceModel.scan()))
        return results

    async def create(self, source_data: dict) -> NewsSourceModel:
        """Create a new source."""
        source = NewsSourceModel(
            source_id=str(uuid.uuid4()),
            name=source_data["name"],
            url=str(source_data["url"]),
            feed_url=source_data.get("feed_url"),
            category=source_data.get("category"),
            priority=source_data.get("priority", 5),
            enabled=source_data.get("enabled", True),
            created_at=now_timestamp(),
        )
        await asyncio.to_thread(source.save)
        return source

    async def update(self, source_id: str, **kwargs) -> NewsSourceModel:
        """Update source."""
        source = await self.get_by_id(source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        for key, value in kwargs.items():
            if hasattr(source, key) and value is not None:
                setattr(source, key, value)

        await asyncio.to_thread(source.save)
        return source

    async def delete(self, source_id: str) -> bool:
        """Delete source."""
        source = await self.get_by_id(source_id)
        if source is None:
            return False
        await asyncio.to_thread(source.delete)
        return True
