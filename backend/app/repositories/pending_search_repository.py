"""Repository for managing pending Tavily search results."""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from app.models.pending_search import PendingSearchModel

logger = logging.getLogger(__name__)


class PendingSearchRepository:
    """Handle CRUD operations for pending search results."""

    async def create(self, search_data: dict) -> PendingSearchModel:
        """Save a pending search result."""
        search = PendingSearchModel(
            search_id=search_data["search_id"],
            query=search_data["query"],
            title=search_data["title"],
            url=search_data["url"],
            snippet=search_data.get("snippet"),
            source=search_data.get("source"),
            created_at=search_data.get("created_at", int(datetime.utcnow().timestamp())),
            updated_at=search_data.get("updated_at", int(datetime.utcnow().timestamp())),
            status="pending",
        )
        await asyncio.to_thread(search.save)
        return search

    async def get_by_id(self, search_id: str) -> Optional[PendingSearchModel]:
        """Get a pending search by ID."""
        try:
            return await asyncio.to_thread(PendingSearchModel.get, search_id)
        except PendingSearchModel.DoesNotExist:
            return None

    async def list_pending(self, limit: int = 100):
        """List all pending searches."""
        try:
            results = await asyncio.to_thread(
                lambda: list(PendingSearchModel.scan(
                    filter_condition=PendingSearchModel.status == "pending",
                    attributes_to_get=[
                        "search_id",
                        "query",
                        "title",
                        "url",
                        "snippet",
                        "source",
                        "created_at",
                        "status",
                    ],
                    limit=limit
                ))
            )
            return results
        except Exception as e:
            logger.error(f"Error listing pending searches: {str(e)}")
            return []

    async def update_status(
        self, search_id: str, status: str, approved_by: Optional[str] = None
    ) -> Optional[PendingSearchModel]:
        """Update search status (pending, approved, rejected)."""
        search = await self.get_by_id(search_id)
        if not search:
            return None

        search.status = status
        search.updated_at = int(datetime.utcnow().timestamp())

        if status == "approved" and approved_by:
            search.approved_by = approved_by
            search.approved_at = int(datetime.utcnow().timestamp())

        await asyncio.to_thread(search.save)
        return search

    async def delete(self, search_id: str) -> bool:
        """Delete a pending search."""
        search = await self.get_by_id(search_id)
        if not search:
            return False

        await asyncio.to_thread(search.delete)
        return True
