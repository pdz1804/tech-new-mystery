"""Article data repository.

Handles all DynamoDB operations for articles using PynamoDB.
Uses async thread pool to run blocking PynamoDB operations.
"""

import asyncio
import logging
from pynamodb.exceptions import DoesNotExist

from app.models.article import ArticleModel
from app.utils.time import now_timestamp

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Repository for article DynamoDB operations.

    Handles all CRUD operations on articles table in DynamoDB.
    - Uses PynamoDB for ORM
    - Runs blocking operations in thread pool
    - Logs all database operations for debugging
    - Supports pagination via GSI
    """

    async def get_by_id(self, article_id: str) -> ArticleModel | None:
        """Get article by ID from DynamoDB.

        Args:
            article_id (str): Article UUID

        Returns:
            ArticleModel or None if not found
        """
        logger.debug(f"Fetching article by ID: {article_id}")
        try:
            article = await asyncio.to_thread(ArticleModel.get, article_id)
            logger.debug(f"Article found: {article.title}")
            return article
        except DoesNotExist:
            logger.debug(f"Article not found: {article_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {type(e).__name__}: {str(e)}")
            raise

    async def get_by_slug(self, slug: str) -> ArticleModel | None:
        """Get article by slug from DynamoDB GSI.

        Args:
            slug (str): Article slug identifier

        Returns:
            ArticleModel or None if not found
        """
        logger.debug(f"Querying article by slug: {slug}")
        try:
            results = await asyncio.to_thread(
                lambda: list(ArticleModel.slug_index.query(slug, limit=1))
            )
            if results:
                logger.debug(f"Article found by slug: {slug}")
                return results[0]
            else:
                logger.debug(f"No article found for slug: {slug}")
                return None
        except Exception as e:
            logger.error(f"Error querying article by slug {slug}: {type(e).__name__}: {str(e)}")
            return None

    async def list_all(self, limit: int = 20, last_key: str | None = None) -> tuple[list[ArticleModel], dict | None]:
        """List all articles with pagination.

        Args:
            limit (int): Maximum items per page (default 20)
            last_key (str): Pagination cursor for next page

        Returns:
            Tuple of (articles_list, next_last_key for pagination)
        """
        logger.debug(f"Scanning articles: limit={limit}, has_last_key={last_key is not None}")
        try:
            results = await asyncio.to_thread(
                lambda: ArticleModel.scan(limit=limit, last_evaluated_key=last_key)
            )
            items = list(results)
            logger.debug(f"Articles scan returned {len(items)} items")
            return items, results.last_evaluated_key
        except Exception as e:
            logger.error(f"Error scanning articles: {type(e).__name__}: {str(e)}")
            raise

    async def create(self, article_data: dict) -> ArticleModel:
        """Create new article in DynamoDB.

        Args:
            article_data (dict): Article data with keys: article_id, title, slug, etc.

        Returns:
            Created ArticleModel instance

        Raises:
            Exception: If database write fails
        """
        article_id = article_data["article_id"]
        title = article_data["title"]
        logger.info(f"Creating article in DynamoDB: {article_id}")
        logger.debug(f"  Title: {title}")
        logger.debug(f"  Category: {article_data.get('category')}")
        logger.debug(f"  URL: {article_data.get('original_url')}")

        try:
            article = ArticleModel(
                article_id=article_data["article_id"],
                title=article_data["title"],
                slug=article_data["slug"],
                source_id=article_data.get("source_id", ""),
                original_url=article_data.get("original_url", ""),
                content=article_data.get("content", ""),
                summary=article_data.get("summary"),
                markdown_content=article_data.get("markdown_content"),
                author=article_data.get("author"),
                category=article_data.get("category"),
                tags=article_data.get("tags", []),
                is_published=article_data.get("is_published", True),
                view_count=0,
                like_count=0,
                published_at=article_data.get("published_at"),
                crawled_at=now_timestamp(),
                created_at=now_timestamp(),
                updated_at=now_timestamp(),
            )
            await asyncio.to_thread(article.save)
            logger.info(f"[SUCCESS] Article created successfully: {article_id}")
            return article
        except Exception as e:
            logger.error(f"[ERROR] Failed to create article {article_id}: {type(e).__name__}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            raise

    async def update(self, article_id: str, **kwargs) -> ArticleModel:
        """Update article in DynamoDB.

        Args:
            article_id (str): Article UUID
            **kwargs: Fields to update

        Returns:
            Updated ArticleModel instance

        Raises:
            ValueError: If article not found
            Exception: If database write fails
        """
        logger.info(f"Updating article: {article_id}")
        logger.debug(f"  Update fields: {list(kwargs.keys())}")

        try:
            article = await self.get_by_id(article_id)
            if article is None:
                logger.error(f"Article not found for update: {article_id}")
                raise ValueError(f"Article {article_id} not found")

            for key, value in kwargs.items():
                if hasattr(article, key) and value is not None:
                    logger.debug(f"  Setting {key} = {value if len(str(value)) < 100 else str(value)[:100] + '...'}")
                    setattr(article, key, value)

            article.updated_at = now_timestamp()
            await asyncio.to_thread(article.save)
            logger.info(f"[SUCCESS] Article updated successfully: {article_id}")
            return article
        except Exception as e:
            logger.error(f"[ERROR] Failed to update article {article_id}: {type(e).__name__}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            raise

    async def delete(self, article_id: str) -> bool:
        """Delete article from DynamoDB.

        Args:
            article_id (str): Article UUID

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting article: {article_id}")
        try:
            article = await self.get_by_id(article_id)
            if article is None:
                logger.warning(f"Article not found for deletion: {article_id}")
                return False
            await asyncio.to_thread(article.delete)
            logger.info(f"[SUCCESS] Article deleted successfully: {article_id}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete article {article_id}: {type(e).__name__}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            raise

    async def list_pending(self) -> list[ArticleModel]:
        """List all pending (unpublished) articles.

        Returns:
            List of unpublished ArticleModel instances
        """
        logger.debug("Scanning for pending articles (is_published=False)")
        try:
            results = await asyncio.to_thread(
                lambda: list(ArticleModel.scan(
                    ArticleModel.is_published == False,
                    limit=1000
                ))
            )
            logger.info(f"Found {len(results)} pending articles")
            return results
        except Exception as e:
            logger.error(f"Error listing pending articles: {type(e).__name__}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            raise
