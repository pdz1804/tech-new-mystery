"""Service for evaluating article quality and technical relevance."""

import json
import logging
import re
import time
from typing import Optional

from app.repositories.article_repository import ArticleRepository
from app.utils.prompt_loader import load_prompt
from app.utils.time import now_timestamp

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for evaluating article technical quality and relevance.

    Uses LLM to score articles 0-10 on tech relevance and content quality.
    """

    def __init__(self, article_repo: Optional[ArticleRepository] = None):
        """Initialize EvaluationService.

        Args:
            article_repo: ArticleRepository instance (lazy-init if None)
        """
        self._article_repo = article_repo

    async def evaluate_article(self, article_id: str) -> Optional[float]:
        """Fetch article, evaluate quality score, save to DB.

        Args:
            article_id: Article ID to evaluate

        Returns:
            Quality score (0.0-10.0) or None if evaluation failed
        """
        import asyncio

        # Lazy init repository
        if self._article_repo is None:
            self._article_repo = ArticleRepository()

        try:
            logger.info(f"[EVALUATE] Starting evaluation for article {article_id}")
            start_time = time.time()

            # Fetch article
            article = await self._article_repo.get_by_id(article_id)
            if not article:
                logger.warning(f"[EVALUATE] Article not found: {article_id}")
                return None

            # Build evaluation prompt
            title = article.title or "Untitled"
            summary = article.summary or ""
            # Use first 1000 chars of markdown content for preview
            content_preview = (
                article.markdown_content[:1000] if article.markdown_content else ""
            )

            prompt = load_prompt("evaluation/evaluate_article.md").format(
                title=title,
                summary=summary,
                content_preview=content_preview,
            )

            logger.debug(f"[EVALUATE] Prompt prepared for {article_id}")

            # Call LLM
            from app.integrations.llm_client import get_llm_client

            llm_client = await get_llm_client()

            # Retry logic
            max_retries = 3
            score = None
            for attempt in range(max_retries):
                try:
                    logger.info(f"[EVALUATE] LLM call attempt {attempt + 1}/{max_retries}")
                    response = await llm_client.generate(
                        prompt=prompt,
                        max_tokens=500,
                        temperature=0.5,
                    )
                    logger.debug(f"[EVALUATE] Raw response: {response[:200]}")

                    # Parse JSON
                    cleaned = response.strip()

                    # Remove markdown code blocks if present
                    if cleaned.startswith("```"):
                        cleaned = re.sub(r"^```(json)?\s*", "", cleaned, flags=re.MULTILINE)
                        cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
                        cleaned = cleaned.strip()

                    try:
                        data = json.loads(cleaned)
                    except json.JSONDecodeError:
                        logger.debug("Initial parse failed, trying to fix newlines")
                        # Fix unescaped newlines
                        start_idx = cleaned.find("{")
                        end_idx = cleaned.rfind("}")
                        if start_idx >= 0 and end_idx > start_idx:
                            json_part = cleaned[start_idx : end_idx + 1]
                            fixed_json = json_part.replace("\n", "\\n")
                            data = json.loads(fixed_json)
                        else:
                            raise

                    # Extract and clamp score
                    score_raw = data.get("score")
                    score = float(score_raw) if score_raw is not None else None
                    if score is not None:
                        score = max(0.0, min(10.0, score))
                        logger.info(f"[EVALUATE] Score extracted: {score}")
                        break
                    else:
                        raise ValueError("No score in response")

                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning(
                        f"[EVALUATE] Attempt {attempt + 1} JSON parse failed: {type(e).__name__}: {str(e)}"
                    )
                    if attempt == max_retries - 1:
                        raise

            if score is None:
                logger.warning(f"[EVALUATE] Failed to extract score after {max_retries} attempts")
                return None

            # Save to DynamoDB
            logger.info(f"[EVALUATE] Saving score {score} to database")
            await self._article_repo.update(article_id, quality_score=score)

            elapsed = time.time() - start_time
            logger.info(f"[EVALUATE] Complete in {elapsed:.2f}s: article_id={article_id}, score={score}")

            return score

        except Exception as e:
            logger.error(
                f"[EVALUATE] Error evaluating article {article_id}: {type(e).__name__}: {str(e)}"
            )
            logger.debug("Error details:", exc_info=True)
            return None
