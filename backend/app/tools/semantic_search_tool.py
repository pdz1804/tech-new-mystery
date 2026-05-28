"""Semantic Search Tool for AI agents - performs vector-based semantic search on articles."""

import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.services.qdrant_service import QdrantService
from app.services.embedding_service import EmbeddingService
from app.repositories.article_repository import ArticleRepository
from app.models.search_result import ArticleResult

logger = logging.getLogger(__name__)


class SemanticSearchTool:
    """Semantic Search Tool for AI agents.

    Performs vector-based semantic search across article embeddings in Qdrant,
    enriches results with metadata from DynamoDB, and calculates engagement scores.

    Responsibilities:
    - Embed search queries using EmbeddingService
    - Search similar articles in Qdrant vector database
    - Fetch and enrich metadata from DynamoDB
    - Calculate engagement scores
    - Apply filters (source, date range)
    - Return top_k ranked results
    """

    def __init__(self):
        """Initialize semantic search tool with required services."""
        self.qdrant_service = QdrantService()
        self.embedding_service = EmbeddingService()
        self.article_repository = ArticleRepository()

    async def execute(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ArticleResult]:
        """
        Execute semantic search on articles.

        Performs vector-based semantic search using embeddings, fetches metadata
        from DynamoDB, applies filters, and returns enriched results ranked by
        relevance.

        Args:
            query: Search query text (e.g., "AI breakthroughs in 2024")
            top_k: Maximum number of results to return (default 10)
            min_score: Minimum relevance score threshold (0.0-1.0, default 0.0)
            filters: Optional dict with filtering criteria:
                - source: str - Filter by news source (e.g., "techcrunch")
                - source_id: str - Filter by source_id (internal ID)
                - start_date: int - Unix timestamp (articles published after)
                - end_date: int - Unix timestamp (articles published before)
                - category: str - Filter by category (e.g., "AI", "tech")

        Returns:
            List[ArticleResult]: Top k articles ranked by relevance_score
                Each result includes article metadata and engagement scoring.

        Raises:
            ValueError: If query is empty or top_k is invalid
            Exception: If embedding or Qdrant service fails
        """
        start_time = time.time()

        # Validate inputs
        if not query or not query.strip():
            logger.warning("Empty query provided to semantic search")
            raise ValueError("Query cannot be empty")

        if top_k < 1 or top_k > 100:
            logger.warning(f"Invalid top_k value: {top_k}, must be 1-100")
            raise ValueError("top_k must be between 1 and 100")

        if min_score < 0.0 or min_score > 1.0:
            logger.warning(f"Invalid min_score value: {min_score}, must be 0.0-1.0")
            raise ValueError("min_score must be between 0.0 and 1.0")

        filters = filters or {}

        logger.info(
            f"Starting semantic search: query='{query}', top_k={top_k}, "
            f"min_score={min_score}, filters={filters}"
        )

        try:
            # Step 1: Generate embedding for query
            logger.debug(f"Generating embedding for query: '{query}'")
            query_embedding = await self.embedding_service.generate_embedding(query)

            if not query_embedding or len(query_embedding) != 1536:
                logger.error(f"Invalid query embedding: got {len(query_embedding) or 0} dims")
                raise Exception("Failed to generate valid query embedding")

            logger.debug(f"Query embedding generated: {len(query_embedding)} dimensions")

            # Step 2: Search Qdrant for similar articles
            logger.debug(f"Searching Qdrant for similar articles (top_k={top_k * 2})")
            # Fetch more than top_k to account for filtering
            qdrant_results = await self._search_qdrant(query_embedding, limit=top_k * 2)

            if not qdrant_results:
                logger.info(f"No results found for query: '{query}'")
                return []

            logger.debug(f"Qdrant returned {len(qdrant_results)} candidate results")

            # Step 3: Filter by score threshold
            logger.debug(f"Filtering by min_score={min_score}")
            qdrant_results = [r for r in qdrant_results if r.get("dense_score", 0) >= min_score]

            if not qdrant_results:
                logger.info(f"No results met min_score threshold {min_score}")
                return []

            logger.debug(f"After score filter: {len(qdrant_results)} results")

            # Step 4: Fetch metadata from DynamoDB and enrich results
            logger.debug("Fetching article metadata from DynamoDB...")
            enriched_results = await self._enrich_results(qdrant_results, filters)

            # Step 5: Sort by relevance and return top_k
            enriched_results = sorted(
                enriched_results,
                key=lambda x: x.relevance_score,
                reverse=True,
            )[:top_k]

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Semantic search completed: query='{query}', "
                f"results={len(enriched_results)}, time={elapsed_ms:.0f}ms"
            )

            return enriched_results

        except Exception as e:
            logger.error(f"Semantic search failed for query '{query}': {str(e)}")
            raise

    async def _search_qdrant(self, query_embedding: List[float], limit: int) -> List[dict]:
        """
        Search Qdrant vector database for similar articles.

        Uses cosine similarity to find articles with similar embeddings.

        Args:
            query_embedding: 1536-dimensional query embedding vector
            limit: Maximum number of results to fetch

        Returns:
            List[dict]: Search results with article_id, slug, title, summary, dense_score
        """
        if not self.qdrant_service.client:
            logger.error("Qdrant client not available")
            raise Exception("Qdrant vector database not available")

        try:
            logger.debug(f"Searching Qdrant collection with limit={limit}")

            from qdrant_client.http import models

            # Search using query_points with cosine similarity
            results = self.qdrant_service.client.query_points(
                collection_name=self.qdrant_service.collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=0.0,  # Include all results, filter later
            )

            # Format results
            formatted = []
            for result in results.points:
                formatted.append({
                    "article_id": result.payload.get("article_id"),
                    "slug": result.payload.get("slug"),
                    "title": result.payload.get("title", ""),
                    "summary": result.payload.get("summary", ""),
                    "category": result.payload.get("category"),
                    "dense_score": result.score,
                    "source_id": result.payload.get("source_id"),
                    "published_at": result.payload.get("published_at"),
                })

            logger.debug(f"Qdrant search returned {len(formatted)} results")
            return formatted

        except Exception as e:
            logger.error(f"Qdrant search failed: {str(e)}")
            raise

    async def _enrich_results(
        self,
        qdrant_results: List[dict],
        filters: Dict[str, Any],
    ) -> List[ArticleResult]:
        """
        Enrich Qdrant results with metadata from DynamoDB.

        Fetches full article metadata, applies filters, calculates engagement scores.

        Args:
            qdrant_results: Results from Qdrant search with article_id, dense_score
            filters: Filtering criteria (source, date range, category)

        Returns:
            List[ArticleResult]: Enriched results with full metadata and engagement scores
        """
        enriched = []

        for result in qdrant_results:
            article_id = result.get("article_id")

            if not article_id:
                logger.warning("Result missing article_id, skipping")
                continue

            try:
                # Fetch full article from DynamoDB
                article = await self.article_repository.get_by_id(article_id)

                if not article:
                    logger.debug(f"Article not found in DynamoDB: {article_id}")
                    continue

                # Apply filters
                if not self._passes_filters(article, filters):
                    logger.debug(f"Article {article_id} filtered out by criteria")
                    continue

                # Calculate engagement score
                engagement_score = self._calculate_engagement_score(article)

                # Create result
                article_result = ArticleResult(
                    article_id=article_id,
                    title=article.title or "",
                    summary=article.summary or "",
                    relevance_score=result.get("dense_score", 0.0),
                    source=article.source_id or "unknown",
                    url=article.original_url or "",
                    published_at=article.published_at,
                    author=article.author,
                    category=article.category,
                    view_count=article.view_count or 0,
                    engagement_score=engagement_score,
                )

                enriched.append(article_result)

            except Exception as e:
                logger.warning(f"Failed to enrich result {article_id}: {str(e)}")
                continue

        logger.debug(f"Enriched {len(enriched)} results from {len(qdrant_results)} candidates")
        return enriched

    def _passes_filters(self, article, filters: Dict[str, Any]) -> bool:
        """
        Check if article passes all filter criteria.

        Args:
            article: ArticleModel instance
            filters: Dict with optional keys: source, source_id, start_date, end_date, category

        Returns:
            bool: True if article passes all filters
        """
        # Filter by source (news source name)
        if "source" in filters and article.source_id != filters["source"]:
            return False

        # Filter by source_id (internal source identifier)
        if "source_id" in filters and article.source_id != filters["source_id"]:
            return False

        # Filter by category
        if "category" in filters and article.category != filters["category"]:
            return False

        # Filter by date range
        published_at = article.published_at or 0

        if "start_date" in filters:
            start_date = filters["start_date"]
            if published_at < start_date:
                return False

        if "end_date" in filters:
            end_date = filters["end_date"]
            if published_at > end_date:
                return False

        return True

    def _calculate_engagement_score(self, article) -> float:
        """
        Calculate engagement score based on article metrics.

        Simple formula: (view_count + like_count) / (max + 1)
        Normalized to 0.0-1.0 range.

        Args:
            article: ArticleModel instance

        Returns:
            float: Engagement score between 0.0 and 1.0
        """
        views = article.view_count or 0
        likes = article.like_count or 0

        # Normalize to 0-1 scale using log scale
        # Prevents extreme outliers from skewing all scores
        import math

        total_engagement = views + (likes * 10)  # Weight likes more heavily
        if total_engagement == 0:
            return 0.0

        # Use logarithmic scaling to normalize
        # log(x+1) ensures 0-engagement gives 0 score
        score = math.log(total_engagement + 1) / math.log(1001)  # normalize to ~0-1
        return min(1.0, score)  # Cap at 1.0

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get tool definition for Agent Core integration.

        Returns schema compatible with Agent Core tool requirements.

        Returns:
            Dict: Tool definition with name, description, and input schema
        """
        return {
            "name": "semantic_search",
            "description": (
                "Search for articles using semantic similarity. Finds articles related to a query "
                "using AI-powered embeddings, returning results ranked by relevance with optional "
                "filtering by source, date range, or category."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text (e.g., 'AI breakthroughs in 2024')",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-100, default 10)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10,
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum relevance score (0.0-1.0, default 0.0)",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.0,
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters to apply",
                        "properties": {
                            "source_id": {
                                "type": "string",
                                "description": "Filter by source ID (e.g., 'techcrunch')",
                            },
                            "category": {
                                "type": "string",
                                "description": "Filter by category (e.g., 'AI', 'tech')",
                            },
                            "start_date": {
                                "type": "integer",
                                "description": "Unix timestamp - articles published after this date",
                            },
                            "end_date": {
                                "type": "integer",
                                "description": "Unix timestamp - articles published before this date",
                            },
                        },
                    },
                },
                "required": ["query"],
            },
            "output_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "article_id": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "relevance_score": {"type": "number"},
                        "source": {"type": "string"},
                        "url": {"type": "string"},
                        "published_at": {"type": "integer"},
                        "author": {"type": "string"},
                        "category": {"type": "string"},
                        "view_count": {"type": "integer"},
                        "engagement_score": {"type": "number"},
                    },
                },
                "description": "List of articles ranked by relevance score",
            },
        }
