#!/usr/bin/env python3
"""Basic test of Crawl4AI AsyncWebCrawler."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_crawler():
    """Test basic crawler functionality."""
    try:
        from crawl4ai import AsyncWebCrawler

        logger.info("Creating AsyncWebCrawler instance...")
        crawler = AsyncWebCrawler()
        logger.info(f"Crawler type: {type(crawler)}")
        logger.info(f"Crawler object: {crawler}")

        logger.info("Testing arun method...")
        result = await crawler.arun(url="https://example.com", bypass_cache=True)
        logger.info(f"Result success: {result.success}")
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result attributes: {dir(result)}")

        return True
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_crawler())
    print(f"Test {'PASSED' if success else 'FAILED'}")
