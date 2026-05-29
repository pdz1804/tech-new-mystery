"""Semantic search tool backed by OpenAI embeddings and Qdrant."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI
from qdrant_client import QdrantClient

from agent_core.config import Settings

logger = logging.getLogger(__name__)


class SemanticSearchTool:
    """Real semantic search integration against the article Qdrant collection."""

    name = "semantic_search"
    description = "Search indexed tech news articles by semantic similarity."

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._qdrant: QdrantClient | None = None
        self._openai: AsyncOpenAI | None = None

        if settings.openai_api_key:
            self._openai = AsyncOpenAI(api_key=settings.openai_api_key)

        if settings.qdrant_mode == "cloud":
            if settings.qdrant_url:
                self._qdrant = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key,
                )
        else:
            self._qdrant = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )

    @property
    def is_configured(self) -> bool:
        """Return whether semantic search has the required external clients."""

        return self._openai is not None and self._qdrant is not None

    async def execute(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Embed the query and search Qdrant for matching articles."""

        query = query.strip()
        if not query:
            raise ValueError("query is required")
        if top_k < 1 or top_k > self.settings.max_search_results:
            raise ValueError(f"top_k must be between 1 and {self.settings.max_search_results}")
        if min_score < 0.0 or min_score > 1.0:
            raise ValueError("min_score must be between 0.0 and 1.0")
        if not self._openai:
            raise RuntimeError("OPENAI_API_KEY is required for semantic search embeddings")
        if not self._qdrant:
            raise RuntimeError("Qdrant configuration is required for semantic search")

        embedding_response = await self._openai.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=query,
        )
        vector = embedding_response.data[0].embedding

        result = await asyncio.to_thread(
            self._qdrant.query_points,
            collection_name=self.settings.qdrant_collection_name,
            query=vector,
            limit=top_k,
            score_threshold=min_score,
        )

        matches: list[dict[str, Any]] = []
        for point in result.points:
            payload = point.payload or {}
            matches.append(
                {
                    "article_id": payload.get("article_id"),
                    "slug": payload.get("slug"),
                    "title": payload.get("title", ""),
                    "summary": payload.get("summary", ""),
                    "url": payload.get("url") or payload.get("original_url"),
                    "source_id": payload.get("source_id"),
                    "category": payload.get("category"),
                    "published_at": payload.get("published_at"),
                    "score": point.score,
                }
            )

        logger.info("semantic_search returned %s results", len(matches))
        return matches


def format_search_results(results: list[dict[str, Any]]) -> str:
    """Format search results into compact context for the LLM."""

    if not results:
        return "No matching articles were found."

    lines = []
    for index, item in enumerate(results, start=1):
        title = item.get("title") or "Untitled"
        summary = item.get("summary") or "No summary available."
        slug = item.get("slug") or item.get("article_id") or "unknown"
        score = item.get("score", 0.0)
        lines.append(f"{index}. {title} (slug: {slug}, score: {score:.3f})\n{summary}")

    return "\n\n".join(lines)

