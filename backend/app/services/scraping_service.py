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
        """Scrape content from URL using Crawl4AI with native media extraction.

        Pipeline:
        1. Validate URL format
        2. Check for unsupported content types (PDF, etc.)
        3. Use enhanced CrawlerClient with media extraction
        4. Execute crawl with JavaScript rendering and media discovery
        5. Process native media items and fallback HTML extraction
        6. Download and upload images to S3
        7. Return structured result with markdown and images

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
        logger.info(f"Starting Crawl4AI scrape with native media extraction: {url}")
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

        try:
            from app.integrations.crawler_client import get_crawler_client

            logger.debug("Getting CrawlerClient instance")
            crawler_client = await get_crawler_client()

            # Use enhanced crawler with native media extraction
            logger.info(f"Crawling URL with native media extraction: {url}")
            crawled_content = await crawler_client.crawl_url(url, use_cache=True)

            elapsed_time = time.time() - start_time
            logger.debug(f"Crawl4AI execution completed in {elapsed_time:.2f} seconds")

            if not crawled_content.success:
                logger.error(f"Crawl4AI failed for {url}: {crawled_content.error}")
                return {
                    "markdown_content": None,
                    "raw_html": None,
                    "success": False,
                    "error": f"Failed to scrape URL: {crawled_content.error}",
                    "images_processed": 0
                }

            logger.debug(f"Crawl4AI extraction successful")
            logger.debug(f"  - Markdown size: {len(crawled_content.markdown)} chars")
            logger.debug(f"  - HTML size: {len(crawled_content.cleaned_html or '')} chars")
            logger.debug(f"  - Media items found: {len(crawled_content.media_items)}")

            # Extract image URLs from native media items first, then fallback to HTML parsing
            image_urls = []
            if crawled_content.media_items:
                image_urls = self._extract_media_urls_from_crawled_content(crawled_content.media_items)
                logger.info(f"Extracted {len(image_urls)} image URLs from native Crawl4AI media extraction")
            else:
                logger.debug("No native media items, falling back to HTML parsing")

            # If no images found via native extraction, try HTML parsing
            if not image_urls and crawled_content.cleaned_html:
                image_urls = self._extract_image_urls_from_html(crawled_content.cleaned_html, url)
                logger.info(f"Extracted {len(image_urls)} image URLs from HTML fallback")

            # Process images: download and upload to S3
            markdown_with_images = crawled_content.markdown
            images_processed = 0

            if image_urls:
                markdown_with_images = await self._process_images(
                    crawled_content.markdown,
                    crawled_content.cleaned_html or "",
                    url,
                    image_urls
                )
                images_processed = sum(1 for url_str in image_urls if url_str in markdown_with_images or f"({url_str})" in markdown_with_images)

            return {
                "markdown_content": markdown_with_images,
                "raw_html": crawled_content.cleaned_html,
                "success": True,
                "error": None,
                "images_processed": images_processed
            }

        except ImportError as e:
            logger.error(f"[ERROR] CRITICAL: Crawl4AI library not installed: {str(e)}")
            logger.error("Install with: pip install crawl4ai")
            return {
                "markdown_content": None,
                "raw_html": None,
                "success": False,
                "error": "Crawl4AI library not installed"
            }
        except ValueError as e:
            logger.warning(f"Invalid URL format for {url}: {str(e)}")
            return {
                "markdown_content": None,
                "raw_html": None,
                "success": False,
                "error": f"Invalid URL format: {str(e)}"
            }
        except Exception as e:
            logger.error(f"[ERROR] Crawl4AI scraping error for {url}: {type(e).__name__}: {str(e)}")
            logger.debug(f"Error traceback:", exc_info=True)

            # Fallback to simple HTML scraper for Windows/Playwright issues
            logger.info(f"Attempting fallback scraper for {url}")
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

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
                "error": None
            }
        except Exception as fallback_error:
            logger.error(f"[ERROR] Fallback scraper failed for {url}: {type(fallback_error).__name__}: {str(fallback_error)}")
            return {
                "markdown_content": None,
                "raw_html": None,
                "success": False,
                "error": f"All scraping methods failed: {str(fallback_error)}"
            }
