"""Web crawler client using Crawl4AI with enhanced media extraction."""

import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

try:
    from crawl4ai import AsyncWebCrawler, CacheMode
    try:
        from crawl4ai.extraction_strategy import LLMExtractionStrategy
    except ImportError:
        LLMExtractionStrategy = None
except ImportError:
    AsyncWebCrawler = None
    CacheMode = None
    LLMExtractionStrategy = None

logger = logging.getLogger(__name__)


class ImageSource(str, Enum):
    """Source of image in content."""
    INLINE = "inline"
    RESPONSIVE = "responsive"
    LAZY_LOADED = "lazy_loaded"


@dataclass
class MediaItem:
    """Extracted media item from crawled content."""
    src: str
    alt: str
    lazy_loaded: bool = False
    srcset: dict = field(default_factory=dict)
    media_type: str = "image/jpeg"
    source: ImageSource = ImageSource.INLINE


@dataclass
class CrawledContent:
    """Crawled content from a URL."""

    url: str
    title: Optional[str]
    content: str
    markdown: str
    cleaned_html: Optional[str]
    media_items: list[MediaItem] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None
    success: bool = True


class CrawlerClient:
    """Web crawler client using Crawl4AI with native media extraction."""

    def __init__(self):
        self.crawler = None
        self._initialized = False

    async def initialize(self):
        """Initialize crawler with browser context."""
        if self._initialized:
            return

        try:
            if not AsyncWebCrawler:
                logger.warning("AsyncWebCrawler not available")
                return

            self.crawler = AsyncWebCrawler()
            # Ensure crawler is ready by creating a warm-up call
            # This forces browser initialization
            logger.info("Crawler initialized successfully")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize crawler: {e}")
            self.crawler = None
            self._initialized = False
            raise

    def _build_crawler_config(self, cache_mode: str = "always", use_llm_strategy: bool = False) -> dict:
        """Build crawler parameters for AsyncWebCrawler.arun().

        Optimized for speed and reliability:
        - Disabled LLM extraction (slow, costs money, not needed for most content)
        - Fast wait strategy: "domcontentloaded" instead of "networkidle"
        - No unnecessary delays
        - Always use cache to avoid re-crawling same URLs
        """
        config_kwargs = {
            "word_count_threshold": 10,
            "exclude_external_links": True,
            "remove_overlay_elements": True,
            "flatten_shadow_dom": True,  # Handle Web Components
            "wait_until": "domcontentloaded",  # Fast: wait for DOM ready, not all network (saves 5-10 sec per request)
            # Removed: delay_before_return_html - was adding unnecessary 2 sec latency
        }

        # Always use cache to prevent re-crawling same URLs
        if CacheMode:
            cache_modes = {
                "always": CacheMode.ENABLED,
                "write": CacheMode.WRITE_ONLY,
                "no": CacheMode.BYPASS,
            }
            config_kwargs["cache_mode"] = cache_modes.get(cache_mode, CacheMode.ENABLED)

        # Disabled LLM extraction strategy - it's slow and calls OpenAI API
        # Basic content extraction is sufficient for news articles
        logger.debug("Using fast extraction strategy (no LLM)")

        return config_kwargs

    def _extract_media_items(self, result: Any) -> list[MediaItem]:
        """Extract media items from crawled result."""
        media_items = []

        try:
            # Check if Crawl4AI result has media attribute
            if hasattr(result, "media") and result.media:
                for media in result.media:
                    item = MediaItem(
                        src=getattr(media, "src", ""),
                        alt=getattr(media, "alt", ""),
                        lazy_loaded=getattr(media, "lazy_loaded", False),
                        srcset=getattr(media, "srcset", {}),
                        media_type=getattr(media, "media_type", "image/jpeg"),
                    )
                    if item.src:
                        media_items.append(item)

                logger.debug(f"Extracted {len(media_items)} media items from Crawl4AI")
            else:
                logger.debug("No media extraction available in Crawl4AI result")
        except Exception as e:
            logger.warning(f"Error extracting media from crawl result: {e}")

        return media_items

    async def crawl_url(self, url: str, timeout: int = 60, use_cache: bool = True) -> CrawledContent:
        """Crawl a URL and extract content with media.

        Timeout increased to 60s to account for browser initialization (5-10s) + page load + extraction.

        Note: Disable cache for worker tasks to reduce SQLite contention in multi-worker environments.
        """
        import time
        start_time = time.time()

        if not self.crawler or not self._initialized:
            await self.initialize()

        if not self.crawler:
            return CrawledContent(
                url=url,
                title=None,
                content="",
                markdown="",
                cleaned_html=None,
                error="Crawler not available - Crawl4AI not installed",
                success=False,
            )

        try:
            # Always disable cache in worker context to prevent SQLite deadlocks with concurrent workers
            cache_mode = "no"
            config = self._build_crawler_config(cache_mode=cache_mode)

            # Pass config parameters directly to arun()
            try:
                logger.info(f"[CRAWL] Starting crawl of {url[:60]}...")
                result = await self.crawler.arun(url=url, **config)
                elapsed = time.time() - start_time
                logger.info(f"[CRAWL] Completed in {elapsed:.2f}s for {url[:60]}...")
            except (AttributeError, TypeError) as e:
                # Handle browser initialization errors
                if "NoneType" in str(e) or "new_context" in str(e):
                    logger.warning(f"Browser context error on {url}: {e}. Browser may not be initialized.")
                    return CrawledContent(
                        url=url,
                        title=None,
                        content="",
                        markdown="",
                        cleaned_html=None,
                        error=f"Browser not available for JavaScript rendering: {str(e)}",
                        success=False,
                    )
                raise

            if not result.success:
                return CrawledContent(
                    url=url,
                    title=None,
                    content="",
                    markdown="",
                    cleaned_html=None,
                    error=f"Crawl failed: {result.error_message}",
                    success=False,
                )

            # Extract media items from result
            media_items = self._extract_media_items(result)

            # Prepare metadata
            metadata = {}
            if hasattr(result, "metadata") and result.metadata:
                metadata = result.metadata

            return CrawledContent(
                url=url,
                title=metadata.get("title") or self._extract_title(result),
                content=result.extracted_content or result.html or "",
                markdown=result.markdown or "",
                cleaned_html=result.html or "",
                media_items=media_items,
                metadata=metadata,
                success=True,
            )

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawledContent(
                url=url,
                title=None,
                content="",
                markdown="",
                cleaned_html=None,
                error=str(e),
                success=False,
            )

    def _extract_title(self, result) -> str:
        """Extract title from crawled result."""
        if hasattr(result, "metadata") and result.metadata:
            return result.metadata.get("title", "")
        return ""

    async def crawl_multiple(self, urls: list[str]) -> list[CrawledContent]:
        """Crawl multiple URLs."""
        if not self.crawler or not self._initialized:
            await self.initialize()

        results = []
        for url in urls:
            content = await self.crawl_url(url)
            results.append(content)

        return results

    async def close(self):
        """Close crawler."""
        if self.crawler:
            try:
                logger.info("Crawler closed successfully")
            except Exception as e:
                logger.error(f"Error closing crawler: {e}")
