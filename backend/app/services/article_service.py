"""Article business logic service.

Handles all article-related operations including creation, retrieval, updates,
deletion, and engagement tracking (likes, saves). Integrates with Crawl4AI for
web scraping and AI services for content processing and metadata generation.
"""

import uuid
import re
import requests
import logging
from datetime import datetime
from urllib.parse import urlparse
from app.core.exceptions import ArticleNotFoundError
from app.repositories.article_repository import ArticleRepository
from app.utils.slug import generate_slug
from app.utils.time import timestamp_to_datetime
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ArticleService:
    """Service for managing articles and article engagement.

    Responsibilities:
    - CRUD operations on articles
    - URL-based article creation with Crawl4AI web scraping
    - AI-powered metadata generation (title, summary, category, tags)
    - User engagement tracking (likes, saves, views)
    - Content serialization and transformation
    """

    def __init__(self, article_repo: ArticleRepository) -> None:
        """Initialize ArticleService.

        Args:
            article_repo: ArticleRepository instance for database operations
        """
        self._article_repo = article_repo
        self._user_likes_repo = None
        logger.debug(f"ArticleService initialized with repository: {article_repo.__class__.__name__}")

    def _serialize_article(self, article) -> dict:
        """Convert article model to dict with proper datetime serialization.

        Args:
            article: Article model instance from repository

        Returns:
            Dictionary with article data and ISO formatted timestamps
        """
        return {
            "article_id": article.article_id,
            "title": article.title,
            "slug": article.slug,
            "summary": article.summary,
            "content": article.content,
            "markdown_content": article.markdown_content,
            "author": article.author,
            "original_url": article.original_url,
            "source_id": article.source_id,
            "preview_image": article.preview_image,
            "category": article.category,
            "tags": article.tags,
            "view_count": article.view_count,
            "like_count": article.like_count,
            "is_published": article.is_published,
            "published_at": timestamp_to_datetime(article.published_at) if article.published_at else None,
            "created_at": timestamp_to_datetime(article.created_at) if article.created_at else None,
        }

    def _serialize_article_detail(self, article) -> dict:
        """Convert article model to detailed dict with proper datetime serialization."""
        return {
            "article_id": article.article_id,
            "title": article.title,
            "slug": article.slug,
            "summary": article.summary,
            "content": article.content,
            "markdown_content": article.markdown_content,
            "author": article.author,
            "original_url": article.original_url,
            "source_id": article.source_id,
            "preview_image": article.preview_image,
            "category": article.category,
            "tags": article.tags,
            "view_count": article.view_count,
            "like_count": article.like_count,
            "is_published": article.is_published,
            "published_at": timestamp_to_datetime(article.published_at) if article.published_at else None,
            "created_at": timestamp_to_datetime(article.created_at) if article.created_at else None,
        }

    async def get_article_by_id(self, article_id: str) -> dict:
        """Get article by ID."""
        article = await self._article_repo.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundError(article_id=article_id)

        return self._serialize_article(article)

    async def get_article_by_slug(self, slug: str) -> dict:
        """Get article by slug.

        Args:
            slug: Article slug identifier

        Returns:
            Serialized article dictionary

        Raises:
            ArticleNotFoundError: If article with slug not found
        """
        logger.debug(f"Fetching article by slug: {slug}")
        article = await self._article_repo.get_by_slug(slug)
        if not article:
            logger.warning(f"Article not found for slug: {slug}")
            raise ArticleNotFoundError(article_id=slug)

        logger.debug(f"Article retrieved successfully: {article.article_id}")
        return self._serialize_article_detail(article)

    async def list_articles(
        self,
        limit: int = 20,
        last_key: str | None = None,
        category: str | None = None,
        source_id: str | None = None,
        tags: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sort_by: str = "created_at",
        **kwargs,
    ) -> dict:
        """List articles with optional filters."""
        articles, next_key = await self._article_repo.list_all(limit=limit, last_key=last_key)

        filtered_articles = articles
        if category:
            filtered_articles = [a for a in filtered_articles if a.category == category]
        if source_id:
            filtered_articles = [a for a in filtered_articles if a.source_id == source_id]
        if tags:
            filtered_articles = [a for a in filtered_articles if any(t in a.tags for t in tags)]

        return {
            "data": [self._serialize_article(a) for a in filtered_articles],
            "meta": {"limit": limit, "last_key": next_key},
        }

    async def create_article(self, article_data: dict) -> dict:
        """Create an article."""
        title = article_data.get("title", "").strip()
        if not title:
            raise ValueError("Article title cannot be empty")

        article_id = str(uuid.uuid4())
        slug = generate_slug(title)

        article = await self._article_repo.create(
            {
                "article_id": article_id,
                "title": title,
                "slug": slug,
                "source_id": article_data.get("source_id", ""),
                "original_url": str(article_data["original_url"]),
                "content": article_data.get("content", ""),
                "summary": article_data.get("summary"),
                "markdown_content": article_data.get("markdown_content"),
                "author": article_data.get("author"),
                "category": article_data.get("category"),
                "tags": article_data.get("tags", []),
                "is_published": True,
            }
        )

        return self._serialize_article_detail(article)

    async def update_article(self, slug: str, update_data: dict) -> dict:
        """Update an article by slug."""
        article = await self._article_repo.get_by_slug(slug)
        if not article:
            raise ArticleNotFoundError(article_id=slug)

        # Validate and prepare update data
        update_fields = {}

        if "title" in update_data and update_data["title"] is not None:
            title = update_data["title"].strip()
            if not title:
                raise ValueError("Title cannot be empty")
            if len(title) > 500:
                raise ValueError("Title must be 500 characters or less")
            update_fields["title"] = title

        if "content" in update_data and update_data["content"] is not None:
            update_fields["content"] = update_data["content"]

        if "author" in update_data and update_data["author"] is not None:
            update_fields["author"] = update_data["author"]

        if "category" in update_data and update_data["category"] is not None:
            update_fields["category"] = update_data["category"]

        if "tags" in update_data and update_data["tags"] is not None:
            update_fields["tags"] = update_data["tags"]

        if "summary" in update_data and update_data["summary"] is not None:
            update_fields["summary"] = update_data["summary"]

        if not update_fields:
            raise ValueError("At least one field must be provided for update")

        # Update via repository
        updated_article = await self._article_repo.update(article.article_id, **update_fields)

        return self._serialize_article_detail(updated_article)

    async def delete_article(self, slug: str) -> bool:
        """Delete an article by slug and clean up associated S3 images."""
        article = await self._article_repo.get_by_slug(slug)
        if not article:
            return False

        # Clean up S3 images before deleting article
        if article.markdown_content:
            from app.services.image_storage_service import ImageStorageService
            image_service = ImageStorageService()
            await image_service.delete_images_from_markdown(article.markdown_content)

        return await self._article_repo.delete(article.article_id)

    async def create_from_url(
        self,
        url: str,
        title: str | None = None,
        author: str | None = None,
        auto_summarize: bool = True
    ) -> dict:
        """Create article from URL with intelligent AI-powered summarization and structuring.

        Pipeline:
        1. Validate URL format
        2. Check for duplicate URLs in system
        3. Scrape content using CRITICAL Crawl4AI (LLM-friendly extraction)
        4. Process with AI to generate title, summary, category, tags
        5. Create article in DynamoDB

        Args:
            url: Article URL to scrape and process
            title: Optional custom title (AI generates if not provided)
            author: Optional author name
            auto_summarize: Whether to auto-generate summary via AI

        Returns:
            Serialized article dictionary with all metadata

        Raises:
            ValueError: Invalid URL, duplicate URL, or empty content
            Exception: Scraping or AI processing failures
        """
        logger.info(f"Starting article creation from URL: {url}")

        # Validate URL format
        logger.debug(f"Validating URL format: {url}")
        try:
            parsed = urlparse(str(url))
            if not parsed.scheme or not parsed.netloc:
                logger.error(f"Invalid URL format: {url}")
                raise ValueError("Invalid URL format")
        except Exception as e:
            logger.error(f"URL validation failed for {url}: {str(e)}")
            raise ValueError(f"Invalid URL: {str(e)}")

        url_str = str(url)

        # Check for duplicate URL
        logger.debug(f"Checking for duplicate URL: {url_str}")
        articles, _ = await self._article_repo.list_all(limit=1000)
        for article in articles:
            if article.original_url == url_str:
                logger.warning(f"Duplicate URL detected: {url_str} (existing article: {article.article_id})")
                raise ValueError("Article from this URL already exists in the system")

        # Scrape content using Crawl4AI (CRITICAL COMPONENT)
        logger.info(f"[ERROR] CRITICAL: Scraping URL with Crawl4AI: {url_str}")
        from app.services.scraping_service import ScrapingService
        scraper = ScrapingService()
        scrape_result = await scraper.scrape_url(url_str)

        if not scrape_result.get("success"):
            error_msg = scrape_result.get('error', 'Unknown error')
            logger.error(f"Crawl4AI scraping failed for {url_str}: {error_msg}")
            raise Exception(f"Failed to scrape URL: {error_msg}")

        raw_content = scrape_result.get("raw_html")
        if not raw_content:
            logger.error(f"No content extracted by Crawl4AI for {url_str}")
            raise ValueError("Failed to extract content from URL")

        logger.debug(f"Crawl4AI extraction successful - content size: {len(raw_content)} chars")

        # Extract image URLs from scraping result
        image_urls = []
        if scrape_result.get("markdown_content"):
            # Extract S3 image URLs from markdown (format: ![](url))
            import re
            image_pattern = r'!\[.*?\]\((https://[^)]+)\)'
            image_urls = re.findall(image_pattern, scrape_result.get("markdown_content", ""))
            logger.debug(f"Extracted {len(image_urls)} image URLs from scraping result")

        # Process content using AI-powered service
        logger.info(f"Processing extracted content with AI (generating title, summary, category, tags, markdown)")
        from app.services.article_processing_service import ArticleProcessingService
        processor = ArticleProcessingService()

        processing_result = await processor.process_url_content(
            url=url_str,
            raw_content=raw_content,
            title=title,
            author=author,
            image_urls=image_urls,
        )

        if not processing_result:
            logger.error(f"AI processing returned empty result for {url_str}")
            raise Exception("Failed to process URL content")

        logger.debug(f"AI processing successful - generated metadata: {list(processing_result.keys())}")

        # Extract processed fields
        generated_title = processing_result.get("title", "Untitled")
        summary = processing_result.get("summary")
        category = processing_result.get("category", "Other")
        tags = processing_result.get("tags", [])
        processed_author = processing_result.get("author") or author
        structured_markdown = processing_result.get("structured_markdown")

        # Extract clean text content from markdown (for content field)
        markdown_content = processing_result.get("structured_markdown")
        content = processor._extract_text_from_html(raw_content)

        # Create article
        article_id = str(uuid.uuid4())
        slug = generate_slug(generated_title)

        logger.debug(f"Creating article record - ID: {article_id}, Slug: {slug}, Category: {category}, Tags: {tags}")

        # Extract first image as preview image
        preview_image = image_urls[0] if image_urls else None

        # Prepare article data
        article_data = {
            "article_id": article_id,
            "title": generated_title,
            "slug": slug,
            "source_id": self._extract_domain(url_str),
            "original_url": url_str,
            "preview_image": preview_image,
            "content": content,
            "summary": summary,
            "markdown_content": structured_markdown,
            "author": processed_author,
            "category": category,
            "tags": tags,
            "is_published": True,
        }

        # Create article in database
        logger.info(f"Saving article to DynamoDB: {article_id}")
        article = await self._article_repo.create(article_data)
        logger.info(f"[SUCCESS] Article created successfully: {article_id} (slug: {slug})")

        return self._serialize_article_detail(article)


    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for source identification."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except:
            return "unknown"

    async def like_article(self, user_id: str, article_id: str) -> dict:
        """Like an article."""
        from app.repositories.user_likes_repository import UserLikesRepository

        if not self._user_likes_repo:
            self._user_likes_repo = UserLikesRepository()

        article = await self._article_repo.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundError(article_id=article_id)

        # Check if already liked
        is_liked = await self._user_likes_repo.is_liked(user_id, article_id)
        if is_liked:
            raise ValueError("Article already liked by this user")

        # Add like and increment counter
        await self._user_likes_repo.like_article(user_id, article_id)
        await self._article_repo.update(article_id, like_count=article.like_count + 1)

        return {"success": True, "message": "Article liked"}

    async def unlike_article(self, user_id: str, article_id: str) -> dict:
        """Unlike an article."""
        from app.repositories.user_likes_repository import UserLikesRepository

        if not self._user_likes_repo:
            self._user_likes_repo = UserLikesRepository()

        article = await self._article_repo.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundError(article_id=article_id)

        # Check if liked
        is_liked = await self._user_likes_repo.is_liked(user_id, article_id)
        if not is_liked:
            raise ValueError("Article not liked by this user")

        # Remove like and decrement counter
        await self._user_likes_repo.unlike_article(user_id, article_id)
        new_count = max(0, article.like_count - 1)
        await self._article_repo.update(article_id, like_count=new_count)

        return {"success": True, "message": "Article unliked"}

    async def get_like_count(self, article_id: str) -> dict:
        """Get the count of likes for an article."""
        article = await self._article_repo.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundError(article_id=article_id)

        return {"article_id": article_id, "like_count": article.like_count}

    async def increment_view_count(self, article_id: str) -> dict:
        """Increment the view count for an article."""
        article = await self._article_repo.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundError(article_id=article_id)

        # Increment and save
        await self._article_repo.update(article_id, view_count=article.view_count + 1)

        return {"article_id": article_id, "view_count": article.view_count + 1}

