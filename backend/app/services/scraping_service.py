"""Web scraping service using Crawl4AI.

[ERROR] CRITICAL COMPONENT: This module contains the core intelligent web scraping
functionality using Crawl4AI - an LLM-friendly web crawler that extracts clean,
structured content from web pages without relying on BeautifulSoup parsing.

Crawl4AI Features:
- JavaScript rendering support
- HTML to Markdown conversion
- Automatic content extraction
- Metadata extraction
- Cache support for duplicate requests
"""

import logging
from typing import Optional
import time
import re
import os
import urllib.parse
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class ScrapingService:
    """Service for intelligent web scraping using Crawl4AI.

    [ERROR] CRITICAL: This is the MAIN component of the application for extracting
    content from web pages. It uses Crawl4AI instead of BeautifulSoup for
    LLM-friendly, intelligent content extraction.

    Uses AsyncWebCrawler from crawl4ai library to:
    - Execute JavaScript on pages
    - Extract clean HTML
    - Convert to markdown format
    - Handle complex page layouts
    - Retry failed requests
    - Extract and upload images to S3
    """

    def __init__(self):
        """Initialize scraping service with image storage."""
        from app.services.image_storage_service import ImageStorageService
        self.image_storage = ImageStorageService()

    def _is_css_documentation(self, content: str) -> bool:
        """Detect if extracted content is CSS docs instead of actual article.

        LinkedIn group posts without auth return CSS metadata/documentation.
        This detects when we've extracted the wrong content type.
        """
        if not content:
            return False

        content_lower = content.lower()
        css_indicators = [
            'css architecture',
            'icon system',
            'stylesheet',
            'design pattern',
            'class=',
            'responsive sizing',
            'animation framework'
        ]

        indicator_count = sum(1 for indicator in css_indicators if indicator in content_lower)
        return indicator_count >= 3

    def _clean_extracted_content(self, markdown: str, url: str) -> str:
        """Clean extracted content by removing common noise patterns.

        Args:
            markdown: Extracted markdown content
            url: Source URL (to identify platform-specific rules)

        Returns:
            Cleaned markdown content
        """
        if not markdown:
            return markdown

        lines = markdown.split('\n')
        filtered_lines = []
        skip_until_empty = False

        for line in lines:
            # Skip CSS/styling content
            if any(pattern in line.lower() for pattern in ['css', 'stylesheet', 'class=', 'style=', '{', '}']):
                continue

            # Skip technical documentation headers for social posts
            if any(pattern in line.lower() for pattern in ['api documentation', 'developer guide', 'technical reference']):
                skip_until_empty = True
                continue

            if skip_until_empty:
                if line.strip() == '':
                    skip_until_empty = False
                continue

            # Skip navigation and metadata
            if any(pattern in line.lower() for pattern in ['home', 'about', 'contact', 'privacy', 'terms', 'cookie']):
                if len(line) < 50:
                    continue

            filtered_lines.append(line)

        # Keep at least some content
        cleaned = '\n'.join(filtered_lines).strip()
        if not cleaned or len(cleaned) < 100:
            return markdown

        return cleaned

    def _extract_image_urls_from_html(self, html: str, base_url: str) -> list[str]:
        """Extract image URLs from HTML content (fallback when native extraction unavailable).

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            List of absolute image URLs
        """
        if not html:
            return []

        image_urls = []

        class ImageExtractor(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == 'img':
                    for attr, value in attrs:
                        if attr == 'src' and value:
                            image_urls.append(value)

        try:
            parser = ImageExtractor()
            parser.feed(html)
        except Exception as e:
            logger.warning(f"Error parsing HTML for images: {str(e)}")

        # Resolve relative URLs
        absolute_urls = []
        for img_url in image_urls:
            try:
                if img_url.startswith('http'):
                    absolute_urls.append(img_url)
                elif img_url.startswith('/'):
                    parsed = urllib.parse.urlparse(base_url)
                    absolute_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                    absolute_urls.append(absolute_url)
                else:
                    absolute_url = urllib.parse.urljoin(base_url, img_url)
                    absolute_urls.append(absolute_url)
            except Exception as e:
                logger.warning(f"Error resolving image URL {img_url}: {str(e)}")

        return absolute_urls

    def _extract_media_urls_from_crawled_content(self, media_items: list) -> list[str]:
        """Extract image URLs from native Crawl4AI media extraction.

        Args:
            media_items: List of MediaItem objects from crawler

        Returns:
            List of absolute image URLs
        """
        if not media_items:
            return []

        urls = []
        for item in media_items:
            try:
                if hasattr(item, 'src') and item.src:
                    urls.append(item.src)
                    # Also add responsive variants if available
                    if hasattr(item, 'srcset') and item.srcset:
                        for variant_url in item.srcset.values():
                            if variant_url and variant_url not in urls:
                                urls.append(variant_url)
            except Exception as e:
                logger.warning(f"Error extracting URL from media item: {str(e)}")

        logger.info(f"Extracted {len(urls)} URLs from {len(media_items)} media items")
        return urls

    async def _process_images(self, markdown: str, html: str, base_url: str, image_urls: list[str] | None = None) -> str:
        """Process images: download and upload to S3, replace URLs in markdown.

        Args:
            markdown: Markdown content
            html: Original HTML content
            base_url: Base URL for resolving relative URLs
            image_urls: Optional list of pre-extracted image URLs (for optimization)

        Returns:
            Markdown with S3 image URLs
        """
        try:
            logger.info(f"Processing images for {base_url}")

            # Use provided image URLs or extract from HTML
            if image_urls is None:
                image_urls = self._extract_image_urls_from_html(html, base_url)
                logger.debug(f"Extracted {len(image_urls)} image URLs from HTML")
            else:
                logger.debug(f"Using {len(image_urls)} pre-extracted image URLs")

            if not image_urls:
                logger.debug("No images found in content")
                return markdown

            logger.info(f"Found {len(image_urls)} images to process")

            # Limit processing to first 5 images to avoid excessive API calls
            image_urls = image_urls[:5]

            processed_markdown = markdown
            images_processed = 0

            for original_url in image_urls:
                try:
                    logger.debug(f"Processing image: {original_url}")

                    s3_url = await self.image_storage.download_and_upload_image(original_url)

                    if s3_url:
                        logger.info(f"Image uploaded to S3: {s3_url}")

                        # Append image to markdown if not already there
                        if original_url not in processed_markdown:
                            processed_markdown += f"\n\n![Article Image]({s3_url})"
                            images_processed += 1
                    else:
                        logger.warning(f"Failed to upload image: {original_url}")

                except Exception as e:
                    logger.error(f"Error processing image {original_url}: {str(e)}")

            logger.info(f"Successfully processed {images_processed} images")
            return processed_markdown

        except Exception as e:
            logger.error(f"Error in image processing: {str(e)}")
            return markdown

    async def scrape_url(self, url: str) -> dict:
        """Scrape content from URL using fallback scraper (requests + BeautifulSoup).

        Pipeline:
        1. Validate URL format
        2. Check for unsupported content types (PDF, etc.)
        3. Use simple requests + BeautifulSoup (no Playwright browser deadlock)
        4. Extract text and convert to markdown
        5. Download and upload images to S3
        6. Return structured result with markdown and images

        Note: Skips Crawl4AI due to AsyncWebCrawler singleton browser context deadlock
        when multiple workers initialize simultaneously. Fallback scraper is more reliable
        in high-concurrency worker environments.

        Args:
            url (str): The URL to scrape

        Returns:
            dict: Result containing:
                - markdown_content (str): LLM-friendly markdown version with images
                - raw_html (str): Original HTML content
                - success (bool): Whether scraping succeeded
                - error (str): Error message if failed
                - images_processed (int): Number of images uploaded to S3

        Raises:
            (No exceptions raised - all errors captured in response dict)

        Example:
            >>> service = ScrapingService()
            >>> result = await service.scrape_url("https://example.com/article")
            >>> if result['success']:
            ...     markdown = result['markdown_content']
            ...     html = result['raw_html']
        """
        logger.info(f"Starting scrape with fallback scraper (no Crawl4AI): {url}")
        start_time = time.time()

        # Validate URL
        logger.debug(f"Validating URL: {url}")
        if not url or not url.strip():
            logger.warning("Empty URL provided")
            return {
                "markdown_content": None,
                "raw_html": None,
                "success": False,
                "error": "URL cannot be empty",
                "images_processed": 0
            }

        url = url.strip()
        logger.debug(f"URL normalized: {url}")

        # Check for unsupported content types
        if url.lower().endswith('.pdf'):
            logger.warning(f"PDF URL provided: {url} - requires special handling")
            return {
                "markdown_content": None,
                "raw_html": None,
                "success": False,
                "error": "PDF URLs require special handling. Use alternative endpoints for PDF content.",
                "images_processed": 0
            }

        # Bypass Crawl4AI entirely - use fallback scraper only
        # Crawl4AI AsyncWebCrawler singleton causes browser deadlock in multi-worker environments
        logger.info(f"Using fallback scraper to avoid Crawl4AI browser deadlock: {url}")
        return await self._fallback_scrape(url)

    async def _fallback_scrape(self, url: str) -> dict:
        """Fallback scraper using requests + BeautifulSoup (no Playwright).

        Used when Crawl4AI fails (e.g., on Windows with Playwright issues).
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            logger.info(f"[ERROR] Using fallback scraper for: {url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            # ✅ FIX: Hard timeout on HTTP request (10s, much faster than Crawl4AI)
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
            except requests.Timeout:
                logger.warning(f"Fallback scraper timeout (10s) for {url}")
                return {
                    "markdown_content": None,
                    "raw_html": None,
                    "success": False,
                    "error": f"Timeout: Site took too long to respond",
                    "images_processed": 0
                }

            html = response.text
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()

            # Extract text content and basic markdown formatting
            text_content = soup.get_text(separator='\n', strip=True)

            # Simple markdown conversion: preserve paragraphs
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            markdown = '\n\n'.join(lines)

            logger.debug(f"Fallback scraper successful for {url}")

            # Process images: download and upload to S3
            markdown_with_images = await self._process_images(markdown, html, url)

            return {
                "markdown_content": markdown_with_images,
                "raw_html": html,
                "success": True,
                "error": None,
                "images_processed": 0
            }
        except Exception as fallback_error:
            logger.error(f"[ERROR] Fallback scraper failed for {url}: {type(fallback_error).__name__}: {str(fallback_error)}")
            return {
                "markdown_content": None,
                "raw_html": None,
                "success": False,
                "error": f"All scraping methods failed: {str(fallback_error)}",
                "images_processed": 0
            }
