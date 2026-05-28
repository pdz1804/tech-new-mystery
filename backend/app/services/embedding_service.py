"""OpenAI Embedding service for generating vector embeddings."""

import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from app.config import settings
from app.models.article_embedding import ArticleEmbeddingModel
from app.models.article import ArticleModel

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI API.

    Uses text-embedding-3-small model:
    - 1536 dimensions
    - Fast and cost-effective
    - Perfect for semantic search and article indexing
    """

    def __init__(self):
        """Initialize embedding service."""
        self.api_key = settings.openai_api_key
        self.model = settings.openai_embedding_model
        self.embedding_dim = 1536

        if not self.api_key:
            logger.warning("OpenAI API key not configured - embeddings will fail")

    async def generate_embedding(self, text: str, max_retries: int = 3) -> List[float]:
        """
        Generate embedding for text using OpenAI API with retry logic.

        Args:
            text: Text to embed (title + summary + content)
            max_retries: Number of retry attempts on failure

        Returns:
            List[float]: Vector embedding of 1536 dimensions

        Raises:
            Exception: If all retry attempts fail
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.embedding_dim

        # Truncate to reasonable length (API has token limits)
        text = text[:8000]

        for attempt in range(max_retries):
            try:
                import openai
                client = openai.OpenAI(api_key=self.api_key)

                logger.debug(f"Generating embedding for text ({len(text)} chars) - attempt {attempt + 1}/{max_retries}")

                response = client.embeddings.create(
                    input=text,
                    model=self.model,
                    dimensions=self.embedding_dim,
                )

                embedding = response.data[0].embedding

                logger.debug(
                    f"Embedding generated successfully - dimensions: {len(embedding)}, "
                    f"first values: {embedding[:3]}"
                )

                return embedding

            except Exception as e:
                logger.warning(
                    f"Embedding generation failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )

                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} embedding generation attempts failed")
                    raise

    async def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 10,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch

        Returns:
            List[List[float]]: List of embeddings, same length as input
        """
        embeddings = []
        total = len(texts)

        logger.info(f"Generating embeddings for {total} texts in batches of {batch_size}")

        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")

            for j, text in enumerate(batch):
                try:
                    embedding = await self.generate_embedding(text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for text {i + j + 1}/{total}: {str(e)}")
                    embeddings.append([0.0] * self.embedding_dim)

        logger.info(f"Batch embedding generation complete: {len(embeddings)}/{total} successful")

        return embeddings

    def prepare_text_for_embedding(
        self,
        title: str,
        summary: str | None = None,
        content: str | None = None,
    ) -> str:
        """
        Prepare article text for embedding by combining title, summary, and content.

        Args:
            title: Article title (required)
            summary: Article summary (optional)
            content: Article content (optional, truncated to 500 chars)

        Returns:
            str: Combined text for embedding
        """
        parts = [title]

        if summary:
            parts.append(summary)

        if content:
            # Use first 500 characters of content for semantic context
            content_preview = content[:500]
            parts.append(content_preview)

        combined_text = " ".join(p for p in parts if p and p.strip())

        logger.debug(
            f"Prepared text for embedding - title: {len(title)}, "
            f"summary: {len(summary or '')}, content: {len(content or '')}, "
            f"total: {len(combined_text)} chars"
        )

        return combined_text

    def _check_cache(self, article_id: str) -> Optional[List[float]]:
        """
        Check if embedding exists in DynamoDB cache.

        Args:
            article_id: Article ID to check

        Returns:
            List[float]: Cached embedding or None if not found
        """
        try:
            embedding_model = ArticleEmbeddingModel.get(article_id)
            logger.debug(f"Cache hit for article {article_id}")
            return embedding_model.embedding
        except ArticleEmbeddingModel.DoesNotExist:
            logger.debug(f"Cache miss for article {article_id}")
            return None
        except Exception as e:
            logger.warning(f"Error checking cache for article {article_id}: {str(e)}")
            return None

    def _store_embedding(
        self, article_id: str, embedding: List[float], timestamp: Optional[int] = None
    ) -> None:
        """
        Store embedding in DynamoDB cache.

        Args:
            article_id: Article ID
            embedding: Vector embedding
            timestamp: Unix timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = int(datetime.utcnow().timestamp())

        try:
            embedding_model = ArticleEmbeddingModel(
                article_id=article_id,
                embedding=embedding,
                model=self.model,
                timestamp=timestamp,
            )
            embedding_model.save()
            logger.debug(f"Stored embedding for article {article_id}")
        except Exception as e:
            logger.error(f"Error storing embedding for article {article_id}: {str(e)}")
            raise

    def batch_embed_articles(
        self,
        articles: List[Dict],
        force_regenerate: bool = False,
    ) -> Dict[str, Dict]:
        """
        Batch embed multiple articles with caching and efficient API usage.

        Args:
            articles: List of article dicts with id, title, summary, content
            force_regenerate: Force regeneration even if cached

        Returns:
            Dict mapping article_id to embedding response:
            {
                "article_id": {
                    "embedding": [...],
                    "model": "text-embedding-3-small",
                    "cached": bool,
                    "timestamp": int
                }
            }

        Raises:
            Exception: If all retry attempts fail
        """
        if not articles:
            logger.debug("No articles provided for embedding")
            return {}

        total_articles = len(articles)
        logger.info(f"Starting batch embedding for {total_articles} articles")

        # Phase 1: Check cache and separate articles
        articles_to_embed = []
        cached_embeddings = {}
        cache_hits = 0

        for article in articles:
            article_id = article.get("id") or article.get("article_id")
            if not article_id:
                logger.warning("Article missing id, skipping")
                continue

            if force_regenerate:
                articles_to_embed.append(article)
            else:
                cached = self._check_cache(article_id)
                if cached:
                    cached_embeddings[article_id] = {
                        "embedding": cached,
                        "model": self.model,
                        "cached": True,
                        "timestamp": int(datetime.utcnow().timestamp()),
                    }
                    cache_hits += 1
                else:
                    articles_to_embed.append(article)

        cache_hit_rate = (cache_hits / total_articles * 100) if total_articles > 0 else 0
        logger.info(
            f"Cache check complete: {cache_hits}/{total_articles} hits ({cache_hit_rate:.1f}%)"
        )

        # Phase 2: Batch API calls for uncached articles
        api_embeddings = {}
        if articles_to_embed:
            api_embeddings = self._batch_api_embeddings(articles_to_embed)

        # Combine results
        result = {**cached_embeddings, **api_embeddings}
        logger.info(
            f"Batch embedding complete: {len(result)}/{total_articles} successful"
        )

        return result

    def _batch_api_embeddings(self, articles: List[Dict]) -> Dict[str, Dict]:
        """
        Call OpenAI API for articles that aren't cached.

        Args:
            articles: Articles needing embeddings

        Returns:
            Dict of article_id -> embedding response
        """
        batch_size = settings.openai_embedding_batch_size
        total = len(articles)
        result = {}

        logger.info(f"Preparing to embed {total} articles via API")

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = articles[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(
                f"Processing API batch {batch_num}/{total_batches} "
                f"({len(batch)} articles)"
            )

            # Prepare texts for embedding
            texts = []
            article_ids = []
            for article in batch:
                article_id = article.get("id") or article.get("article_id")
                text = self.prepare_text_for_embedding(
                    title=article.get("title", ""),
                    summary=article.get("summary"),
                    content=article.get("content"),
                )
                texts.append(text)
                article_ids.append(article_id)

            # Call API with retry logic
            embeddings = self._call_api_with_retry(texts)

            # Store and collect results
            timestamp = int(datetime.utcnow().timestamp())
            for article_id, embedding in zip(article_ids, embeddings):
                if embedding:
                    self._store_embedding(article_id, embedding, timestamp)
                    result[article_id] = {
                        "embedding": embedding,
                        "model": self.model,
                        "cached": False,
                        "timestamp": timestamp,
                    }
                else:
                    logger.warning(f"Failed to get embedding for article {article_id}")

        return result

    def _call_api_with_retry(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Call OpenAI API with exponential backoff retry.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (or None for failures)
        """
        max_retries = settings.openai_embedding_retry_max_attempts
        backoff_times = [2 ** attempt for attempt in range(max_retries)]

        for attempt in range(max_retries):
            try:
                import openai

                client = openai.OpenAI(api_key=self.api_key)

                logger.debug(
                    f"API call attempt {attempt + 1}/{max_retries} for {len(texts)} texts"
                )

                response = client.embeddings.create(
                    input=texts,
                    model=self.model,
                    dimensions=self.embedding_dim,
                )

                # Extract embeddings in order
                embeddings = []
                for item in response.data:
                    embeddings.append(item.embedding)

                logger.debug(
                    f"API call successful: {len(embeddings)} embeddings received"
                )

                return embeddings

            except Exception as e:
                logger.warning(
                    f"API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )

                if attempt < max_retries - 1:
                    wait_time = backoff_times[attempt]
                    logger.info(f"Retrying in {wait_time} seconds...")
                    asyncio.run(asyncio.sleep(wait_time))
                else:
                    logger.error(f"All {max_retries} API attempts failed")
                    raise Exception(
                        f"Failed to call OpenAI embedding API after {max_retries} attempts: {str(e)}"
                    ) from e

        return [None] * len(texts)
