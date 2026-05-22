"""Qdrant vector database service for semantic search and article indexing."""

import logging
import time
from typing import List, Optional, Tuple
from uuid import UUID
from app.config import settings
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for managing article vectors in Qdrant vector database.

    Responsibilities:
    - Initialize and manage Qdrant client
    - Create/verify collection schema
    - CRUD operations (index, update, delete articles)
    - Hybrid search (dense + BM25)
    - Graceful error handling for unavailable Qdrant
    """

    def __init__(self):
        """Initialize Qdrant service."""
        self.embedding_service = EmbeddingService()
        self.collection_name = settings.qdrant_collection_name
        self.embedding_dim = 1536
        self.client = None

        try:
            self._initialize_client()
        except Exception as e:
            logger.warning(f"Failed to initialize Qdrant client on startup: {str(e)}")
            # Don't raise - allow app to start even if Qdrant is unavailable

    def _initialize_client(self):
        """Initialize Qdrant client based on mode (docker or cloud)."""
        from qdrant_client import QdrantClient
        from qdrant_client.http import models

        try:
            if settings.qdrant_mode == "cloud":
                logger.info(f"Initializing Qdrant client in CLOUD mode: {settings.qdrant_url}")
                self.client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key,
                )
            else:  # docker mode
                logger.info(f"Initializing Qdrant client in DOCKER mode: {settings.qdrant_host}:{settings.qdrant_port}")
                self.client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                )

            logger.info("Qdrant client initialized successfully")

            # Verify/create collection
            self._ensure_collection_exists()

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")
            self.client = None
            raise

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist with proper schema."""
        from qdrant_client.http import models

        if not self.client:
            logger.warning("Qdrant client not available - cannot ensure collection exists")
            return

        try:
            # Check if collection exists
            try:
                info = self.client.get_collection(self.collection_name)
                logger.info(f"Collection '{self.collection_name}' already exists with {info.points_count} points")
                return
            except Exception:
                logger.info(f"Collection '{self.collection_name}' does not exist - creating...")

            # Create collection with dense vectors (COSINE distance for semantic search)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_dim,
                    distance=models.Distance.COSINE,
                ),
            )

            logger.info(
                f"Collection '{self.collection_name}' created successfully "
                f"with {self.embedding_dim}-dim dense vectors (COSINE distance)"
            )

        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {str(e)}")
            raise

    async def index_article(
        self,
        article_id: str,
        title: str,
        slug: str | None = None,
        summary: str | None = None,
        content: str | None = None,
        category: str | None = None,
        author: str | None = None,
        published_at: int | None = None,
        view_count: int = 0,
        source_id: str | None = None,
    ) -> bool:
        """
        Index an article in Qdrant by generating embedding and storing vector + metadata.

        Args:
            article_id: Unique article identifier
            title: Article title (required)
            slug: Public article slug used by the frontend detail route
            summary: Article summary (optional)
            content: Article content (optional)
            category: Article category (optional)
            author: Article author (optional)
            published_at: Publication timestamp (optional)
            view_count: Number of views (default 0)
            source_id: News source ID (optional)

        Returns:
            bool: True if indexed successfully, False otherwise
        """
        if not self.client:
            logger.warning(f"Qdrant client unavailable - article {article_id} not indexed")
            return False

        start_time = time.time()

        try:
            # Generate embedding
            logger.debug(f"Generating embedding for article {article_id}")
            text_for_embedding = self.embedding_service.prepare_text_for_embedding(
                title=title,
                summary=summary,
                content=content,
            )

            embedding = await self.embedding_service.generate_embedding(text_for_embedding)

            if not embedding or len(embedding) != self.embedding_dim:
                logger.error(f"Invalid embedding for article {article_id}: got {len(embedding)} dims")
                return False

            # Prepare payload (metadata)
            payload = {
                "article_id": article_id,
                "slug": slug or article_id,
                "title": title,
                "summary": summary or "",
                "content": content[:1000] if content else "",  # Store first 1000 chars for context
                "category": category or "other",
                "author": author or "unknown",
                "published_at": published_at or 0,
                "view_count": view_count,
                "source_id": source_id or "unknown",
            }

            # Convert article_id string to UUID for Qdrant point ID
            try:
                point_id = int(UUID(article_id).int % (2**63))
            except ValueError:
                # Fallback if not valid UUID
                point_id = hash(article_id) % (2**63)

            # Upsert point in Qdrant (insert or update if exists)
            from qdrant_client.http import models

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Article {article_id} indexed successfully (embedding_time={elapsed_ms:.0f}ms)")

            return True

        except Exception as e:
            logger.error(f"Failed to index article {article_id}: {str(e)}")
            return False

    async def update_article(
        self,
        article_id: str,
        title: str,
        slug: str | None = None,
        summary: str | None = None,
        content: str | None = None,
        category: str | None = None,
        author: str | None = None,
        published_at: int | None = None,
        view_count: int = 0,
        source_id: str | None = None,
    ) -> bool:
        """
        Update an article's embedding and metadata in Qdrant.

        Args:
            article_id: Unique article identifier
            title: Article title (required)
            slug: Public article slug used by the frontend detail route
            summary: Article summary (optional)
            content: Article content (optional)
            category: Article category (optional)
            author: Article author (optional)
            published_at: Publication timestamp (optional)
            view_count: Number of views (default 0)
            source_id: News source ID (optional)

        Returns:
            bool: True if updated successfully, False otherwise
        """
        logger.debug(f"Updating article {article_id} in Qdrant")
        # Upsert operation handles both insert and update
        return await self.index_article(
            article_id=article_id,
            slug=slug,
            title=title,
            summary=summary,
            content=content,
            category=category,
            author=author,
            published_at=published_at,
            view_count=view_count,
            source_id=source_id,
        )

    async def delete_article(self, article_id: str) -> bool:
        """
        Delete an article from Qdrant collection.

        Args:
            article_id: Unique article identifier

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not self.client:
            logger.warning(f"Qdrant client unavailable - cannot delete article {article_id}")
            return False

        try:
            # Convert article_id to point ID (same conversion as index_article)
            try:
                point_id = int(UUID(article_id).int % (2**63))
            except ValueError:
                point_id = hash(article_id) % (2**63)

            from qdrant_client.http import models

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[point_id]),
            )

            logger.info(f"Article {article_id} deleted from Qdrant")
            return True

        except Exception as e:
            logger.warning(f"Failed to delete article {article_id} from Qdrant: {str(e)}")
            # Don't raise - continue even if deletion fails
            return False

    async def article_exists(self, article_id: str) -> bool:
        """
        Check if article exists in Qdrant collection.

        Args:
            article_id: Unique article identifier

        Returns:
            bool: True if exists, False otherwise
        """
        if not self.client:
            return False

        try:
            try:
                point_id = int(UUID(article_id).int % (2**63))
            except ValueError:
                point_id = hash(article_id) % (2**63)

            # Try to retrieve point
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
            )

            exists = len(result) > 0
            logger.debug(f"Article {article_id} exists in Qdrant: {exists}")
            return exists

        except Exception as e:
            logger.debug(f"Failed to check if article {article_id} exists: {str(e)}")
            return False

    async def dense_search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[dict]:
        """
        Perform semantic search using dense vector embeddings.

        Args:
            query: Search query text
            limit: Maximum number of results

        Returns:
            List[dict]: Search results with scores and metadata
        """
        if not self.client:
            logger.warning("Qdrant client unavailable - dense search failed")
            return []

        try:
            logger.debug(f"Performing dense search: query='{query}', limit={limit}")

            # Generate embedding for query
            query_embedding = await self.embedding_service.generate_embedding(query)

            # Search in Qdrant using query_points with vector
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=0.0,  # Include all results, ranked by score
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
                })

            logger.debug(f"Dense search returned {len(formatted)} results")
            return formatted

        except Exception as e:
            logger.error(f"Dense search failed for query '{query}': {str(e)}")
            return []

    async def bm25_search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[dict]:
        """
        Perform keyword search using BM25 index on title and summary.

        Args:
            query: Search query text
            limit: Maximum number of results

        Returns:
            List[dict]: Search results with scores and metadata
        """
        if not self.client:
            logger.warning("Qdrant client unavailable - BM25 search failed")
            return []

        try:
            logger.debug(f"Performing BM25 search: query='{query}', limit={limit}")

            # Search using BM25 on text fields
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,  # Get all points for filtering
            )

            # Manual BM25-like scoring on retrieved points
            query_lower = query.lower()
            scored_results = []

            for point in results[0]:  # scroll returns (points, next_page_offset)
                title = point.payload.get("title", "").lower()
                summary = point.payload.get("summary", "").lower()

                # Simple BM25-like scoring
                score = 0.0

                # Title matches: higher weight
                if query_lower in title:
                    title_matches = title.count(query_lower)
                    score += title_matches * 2.0

                # Summary matches: lower weight
                if query_lower in summary:
                    summary_matches = summary.count(query_lower)
                    score += summary_matches * 0.5

                if score > 0:
                    scored_results.append((score, point))

            # Sort by score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)

            # Format results
            formatted = []
            for score, point in scored_results[:limit]:
                formatted.append({
                    "article_id": point.payload.get("article_id"),
                    "slug": point.payload.get("slug"),
                    "title": point.payload.get("title", ""),
                    "summary": point.payload.get("summary", ""),
                    "category": point.payload.get("category"),
                    "bm25_score": score,
                })

            logger.debug(f"BM25 search returned {len(formatted)} results")
            return formatted

        except Exception as e:
            logger.error(f"BM25 search failed for query '{query}': {str(e)}")
            return []

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        dense_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> List[dict]:
        """
        Perform hybrid search combining dense embeddings and BM25 keyword matching.

        Two-phase approach:
        1. Dense search: Semantic similarity using embeddings
        2. BM25 search: Keyword matching on title and summary
        3. Merge: Combine scores with configurable weights

        Args:
            query: Search query text
            limit: Maximum number of results
            dense_weight: Weight for dense search scores (default 0.6)
            bm25_weight: Weight for BM25 scores (default 0.4)

        Returns:
            List[dict]: Hybrid search results ranked by combined score
        """
        start_time = time.time()

        try:
            logger.info(
                f"Performing hybrid search: query='{query}', limit={limit}, "
                f"dense_weight={dense_weight}, bm25_weight={bm25_weight}"
            )

            # Phase 1: Dense search
            dense_results = await self.dense_search(query, limit=limit * 2)

            # Phase 2: BM25 search
            bm25_results = await self.bm25_search(query, limit=limit * 2)

            # Phase 3: Merge and score
            merged = {}

            # Add dense results
            for result in dense_results:
                article_id = result["article_id"]
                merged[article_id] = {
                    "article_id": article_id,
                    "slug": result.get("slug"),
                    "title": result["title"],
                    "summary": result["summary"],
                    "category": result["category"],
                    "dense_score": result["dense_score"],
                    "bm25_score": 0.0,
                    "hybrid_score": 0.0,
                }

            # Add/update with BM25 results
            for result in bm25_results:
                article_id = result["article_id"]
                if article_id not in merged:
                    merged[article_id] = {
                        "article_id": article_id,
                        "slug": result.get("slug"),
                        "title": result["title"],
                        "summary": result["summary"],
                        "category": result["category"],
                        "dense_score": 0.0,
                        "bm25_score": result["bm25_score"],
                        "hybrid_score": 0.0,
                    }
                else:
                    merged[article_id]["bm25_score"] = result["bm25_score"]

            # Calculate hybrid scores
            for article_id, data in merged.items():
                # Normalize scores (dense is 0-1, bm25 varies)
                normalized_dense = data["dense_score"]  # Already 0-1
                max_bm25 = max((r["bm25_score"] for r in bm25_results), default=1.0)
                normalized_bm25 = data["bm25_score"] / max_bm25 if max_bm25 > 0 else 0.0

                # Combine with weights
                hybrid_score = (
                    normalized_dense * dense_weight +
                    normalized_bm25 * bm25_weight
                )
                merged[article_id]["hybrid_score"] = hybrid_score

            # Sort by hybrid score and return top results
            sorted_results = sorted(
                merged.values(),
                key=lambda x: x["hybrid_score"],
                reverse=True,
            )[:limit]

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Hybrid search completed: query='{query}', results={len(sorted_results)}, "
                f"time={elapsed_ms:.0f}ms"
            )

            return sorted_results

        except Exception as e:
            logger.error(f"Hybrid search failed for query '{query}': {str(e)}")
            return []

    async def get_collection_stats(self) -> dict:
        """
        Get statistics about the collection.

        Returns:
            dict: Collection stats (points count, vectors count, etc.)
        """
        if not self.client:
            logger.warning("Qdrant client unavailable - cannot get collection stats")
            return {"points_count": 0, "error": "Qdrant client unavailable"}

        try:
            info = self.client.get_collection(self.collection_name)
            logger.debug(f"Collection stats: {info.points_count} points")

            return {
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count if hasattr(info, "vectors_count") else info.points_count,
                "status": str(info.status),
            }

        except Exception as e:
            logger.warning(f"Failed to get collection stats: {str(e)}")
            return {"error": str(e)}
