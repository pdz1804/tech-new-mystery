"""OpenAI Embedding service for generating vector embeddings."""

import logging
import asyncio
from typing import List
from app.config import settings

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
