"""Web crawler client using Crawl4AI with enhanced media extraction."""

import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
    try:
        from crawl4ai import BrowserConfig
    except ImportError:
        BrowserConfig = None
    try:
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        from crawl4ai.content_filter_strategy import PruningContentFilter
    except ImportError:
        DefaultMarkdownGenerator = None
        PruningContentFilter = None
except ImportError:
    AsyncWebCrawler = None
    CrawlerRunConfig = None
    BrowserConfig = None
    CacheMode = None
    DefaultMarkdownGenerator = None
    PruningContentFilter = None

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

    async def initialize(self):
        """Initialize crawler."""
        try:
            if BrowserConfig:
                browser_config = BrowserConfig(headless=True)
                self.crawler = AsyncWebCrawler(config=browser_config)
            else:
                self.crawler = AsyncWebCrawler()
            await self.crawler.__aenter__()
            logger.info("Crawler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize crawler: {e}")
            raise

    def _build_crawler_config(self, cache_mode: str = "always") -> Any:
        """Build enhanced CrawlerRunConfig with media extraction and caching."""
        if not CrawlerRunConfig:
            return None

        config_kwargs = {
            "wait_for": "body",
            "js_code": "window.scrollTo(0, document.body.scrollHeight);",
            "remove_overlay_elements": True,
        }

        # Add cache mode if available
        if CacheMode:
            cache_modes = {
                "always": CacheMode.ALWAYS,
                "write": CacheMode.WRITE_ONLY,
                "no": CacheMode.NO_CACHE,
            }
            config_kwargs["cache_mode"] = cache_modes.get(cache_mode, CacheMode.ALWAYS)

        # Add enhanced markdown generation with media extraction
        if DefaultMarkdownGenerator and PruningContentFilter:
            try:
                config_kwargs["markdown_generator"] = DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter(threshold=0.48, threshold_type="fixed"),
                )
            except Exception as e:
                logger.warning(f"Failed to configure advanced markdown generation: {e}")

        return CrawlerRunConfig(**config_kwargs)

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

    async def crawl_url(self, url: str, timeout: int = 30, use_cache: bool = True) -> CrawledContent:
        """Crawl a URL and extract content with media."""
        if not self.crawler:
            await self.initialize()

        try:
            cache_mode = "always" if use_cache else "no"
            config = self._build_crawler_config(cache_mode=cache_mode)

            if config:
                result = await self.crawler.arun(url=url, config=config)
            else:
                result = await self.crawler.arun(url=url)

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
                content=result.text or "",
                markdown=result.markdown or "",
                cleaned_html=result.cleaned_html or "",
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
        if not self.crawler:
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
                await self.crawler.__aexit__(None, None, None)
                logger.info("Crawler closed successfully")
            except Exception as e:
                logger.error(f"Error closing crawler: {e}")


# Singleton instance
_crawler_client: Optional[CrawlerClient] = None


async def get_crawler_client() -> CrawlerClient:
    """Get or create crawler client instance."""
    global _crawler_client
    if _crawler_client is None:
        _crawler_client = CrawlerClient()
        await _crawler_client.initialize()
    return _crawler_client


async def shutdown_crawler():
    """Shutdown crawler client."""
    global _crawler_client
    if _crawler_client:
        await _crawler_client.close()
        _crawler_client = None
