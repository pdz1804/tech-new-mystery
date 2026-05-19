"""Article summarization service using LLM."""

import asyncio
import logging
from typing import Optional

from app.integrations.llm_client import get_llm_client
from app.repositories.article_repository import ArticleRepository

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for article summarization using LLM."""

    def __init__(self, article_repository: ArticleRepository):
        self.article_repo = article_repository

    async def summarize_article(
        self,
        article_id: str,
        max_tokens: int = 300,
        temperature: float = 0.5,
    ) -> Optional[str]:
        """Summarize a single article using LLM."""
        try:
            # Get article from repository
            article = await self.article_repo.get(article_id)
            if not article:
                logger.warning(f"Article {article_id} not found for summarization")
                return None

            # Extract content to summarize
            content = article.content or article.summary or ""
            if not content:
                logger.warning(f"Article {article_id} has no content to summarize")
                return None

            # Truncate content if too long (avoid token limits)
            max_length = 3000
            if len(content) > max_length:
                content = content[:max_length] + "..."

            # Create summarization prompt
            prompt = f"""Please provide a concise summary of the following article in 2-3 sentences. Focus on the main points and key findings.

Article Title: {article.title}

Content:
{content}

Summary:"""

            # Get LLM client and generate summary
            llm_client = await get_llm_client()
            summary = await llm_client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            logger.info(f"Successfully summarized article {article_id}")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error summarizing article {article_id}: {e}")
            return None

    async def extract_citations(
        self,
        article_id: str,
        summary: str,
    ) -> list[dict]:
        """Extract citations and key entities from article content."""
        try:
            article = await self.article_repo.get(article_id)
            if not article:
                return []

            # Create extraction prompt
            prompt = f"""Extract the key citations, statistics, and entities mentioned in the following article content. Return as a JSON list with format: [{{"type": "citation|statistic|entity", "text": "...", "source": "..."}}]

Article Title: {article.title}

Content:
{article.content or ""}

Extracted Citations:"""

            llm_client = await get_llm_client()
            response = await llm_client.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3,
            )

            # Try to parse as JSON, fallback to empty list if parsing fails
            try:
                import json

                citations = json.loads(response)
                return citations if isinstance(citations, list) else []
            except Exception:
                logger.warning(f"Could not parse citations for article {article_id}")
                return []

        except Exception as e:
            logger.error(f"Error extracting citations from article {article_id}: {e}")
            return []

    async def classify_category(
        self,
        article_id: str,
    ) -> Optional[str]:
        """Classify article into a category using LLM."""
        try:
            article = await self.article_repo.get(article_id)
            if not article:
                return None

            categories = [
                "Technology",
                "Business",
                "Science",
                "Health",
                "Politics",
                "Entertainment",
                "Sports",
                "Other",
            ]

            prompt = f"""Classify the following article into one of these categories: {', '.join(categories)}

Article Title: {article.title}

Content:
{article.content or ""}

Category:"""

            llm_client = await get_llm_client()
            category = await llm_client.generate(
                prompt=prompt,
                max_tokens=50,
                temperature=0.3,
            )

            category = category.strip()
            if category in categories:
                return category

            # Return the first category if LLM returns something unexpected
            return categories[0]

        except Exception as e:
            logger.error(f"Error classifying article {article_id}: {e}")
            return None

    async def batch_summarize(
        self,
        article_ids: list[str],
        batch_size: int = 5,
    ) -> dict[str, Optional[str]]:
        """Summarize multiple articles in batches."""
        results = {}

        # Process in batches to avoid overwhelming the LLM API
        for i in range(0, len(article_ids), batch_size):
            batch = article_ids[i : i + batch_size]
            tasks = [self.summarize_article(article_id) for article_id in batch]

            batch_results = await asyncio.gather(*tasks, return_exceptions=False)

            for article_id, summary in zip(batch, batch_results):
                results[article_id] = summary

            # Small delay between batches to be respectful to API
            if i + batch_size < len(article_ids):
                await asyncio.sleep(1)

        return results
