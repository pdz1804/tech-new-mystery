#!/usr/bin/env python3
"""Test Crawl4AI with a real URL (LinkedIn)."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_linkedin_crawl():
    """Test crawling a real LinkedIn post."""
    try:
        from app.integrations.crawler_client import CrawlerClient

        logger.info("=" * 60)
        logger.info("TEST: Real LinkedIn URL with Media Extraction")
        logger.info("=" * 60)

        client = CrawlerClient()
        await client.initialize()

        # LinkedIn GraphRAG post URL from the user
        test_url = "https://www.linkedin.com/posts/pauliusztin_ive-spent-the-past-year-building-graphrag-share-7449366886603128833-X0jR"
        logger.info(f"Testing with LinkedIn URL: {test_url[:80]}...")

        content = await client.crawl_url(test_url, use_cache=False)

        logger.info(f"✓ Crawl Success: {content.success}")
        logger.info(f"  - URL: {content.url}")
        logger.info(f"  - Title: {content.title[:60] if content.title else 'None'}")
        logger.info(f"  - Markdown length: {len(content.markdown)} chars")
        logger.info(f"  - HTML length: {len(content.cleaned_html or '')} chars")
        logger.info(f"  - Media items found: {len(content.media_items)}")

        if content.media_items:
            logger.info("  - Media items:")
            for i, item in enumerate(content.media_items[:5], 1):
                logger.info(f"    {i}. src={item.src[:60]}... alt={item.alt[:40]}")
                if item.srcset:
                    logger.info(f"       srcset variants: {list(item.srcset.keys())}")

        if content.error:
            logger.warning(f"  - Error: {content.error}")

        await client.close()
        logger.info("✓ Test completed\n")
        return content.success

    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_scraping_service():
    """Test scraping service with LinkedIn URL."""
    try:
        from app.services.scraping_service import ScrapingService

        logger.info("=" * 60)
        logger.info("TEST: ScrapingService with LinkedIn URL")
        logger.info("=" * 60)

        service = ScrapingService()

        test_url = "https://www.linkedin.com/posts/pauliusztin_ive-spent-the-past-year-building-graphrag-share-7449366886603128833-X0jR"
        logger.info(f"Testing scraping service with: {test_url[:80]}...")

        result = await service.scrape_url(test_url)

        logger.info(f"✓ Scrape Success: {result['success']}")
        logger.info(f"  - Markdown length: {len(result['markdown_content']) if result['markdown_content'] else 0} chars")
        logger.info(f"  - HTML length: {len(result['raw_html']) if result['raw_html'] else 0} chars")
        logger.info(f"  - Images processed: {result.get('images_processed', 0)}")

        if result.get('error'):
            logger.warning(f"  - Error: {result['error']}")

        logger.info("✓ Test completed\n")
        return result['success']

    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " REAL URL CRAWL4AI TEST ".center(58) + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    results = {}
    results["LinkedInCrawl"] = await test_linkedin_crawl()
    results["ScrapingService"] = await test_scraping_service()

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")
    logger.info("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
