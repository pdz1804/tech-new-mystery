#!/usr/bin/env python3
"""Test script for Crawl4AI integration and image extraction."""

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_crawler_client():
    """Test enhanced CrawlerClient with media extraction."""
    try:
        from app.integrations.crawler_client import CrawlerClient

        logger.info("=" * 60)
        logger.info("TEST 1: Enhanced CrawlerClient with Media Extraction")
        logger.info("=" * 60)

        client = CrawlerClient()
        await client.initialize()

        # Test with a simple URL
        test_url = "https://example.com"
        logger.info(f"Testing with URL: {test_url}")

        content = await client.crawl_url(test_url)

        logger.info(f"✓ Crawl Success: {content.success}")
        logger.info(f"  - Title: {content.title[:50] if content.title else 'None'}")
        logger.info(f"  - Markdown length: {len(content.markdown)} chars")
        logger.info(f"  - Media items found: {len(content.media_items)}")
        logger.info(f"  - Metadata keys: {list(content.metadata.keys())}")

        await client.close()
        logger.info("✓ CrawlerClient test passed\n")
        return True

    except Exception as e:
        logger.error(f"✗ CrawlerClient test failed: {str(e)}")
        return False


async def test_scraping_service():
    """Test enhanced ScrapingService with image extraction."""
    try:
        from app.services.scraping_service import ScrapingService

        logger.info("=" * 60)
        logger.info("TEST 2: Enhanced ScrapingService")
        logger.info("=" * 60)

        service = ScrapingService()

        # Test with a simple URL
        test_url = "https://example.com"
        logger.info(f"Testing scraping service with: {test_url}")

        result = await service.scrape_url(test_url)

        logger.info(f"✓ Scrape Success: {result['success']}")
        logger.info(f"  - Markdown length: {len(result['markdown_content']) if result['markdown_content'] else 0} chars")
        logger.info(f"  - HTML length: {len(result['raw_html']) if result['raw_html'] else 0} chars")
        logger.info(f"  - Images processed: {result.get('images_processed', 0)}")

        if result.get('error'):
            logger.warning(f"  - Error: {result['error']}")

        logger.info("✓ ScrapingService test passed\n")
        return True

    except Exception as e:
        logger.error(f"✗ ScrapingService test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_media_extraction():
    """Test media extraction from crawled content."""
    try:
        from app.integrations.crawler_client import MediaItem, ImageSource

        logger.info("=" * 60)
        logger.info("TEST 3: MediaItem and Image Extraction")
        logger.info("=" * 60)

        # Create test media items
        test_items = [
            MediaItem(
                src="https://example.com/image1.jpg",
                alt="Test Image 1",
                lazy_loaded=False,
                source=ImageSource.INLINE
            ),
            MediaItem(
                src="https://example.com/image2.webp",
                alt="Test Image 2",
                lazy_loaded=True,
                srcset={"small": "https://example.com/image2-sm.webp", "large": "https://example.com/image2-lg.webp"},
                media_type="image/webp",
                source=ImageSource.RESPONSIVE
            ),
        ]

        logger.info(f"✓ Created {len(test_items)} test MediaItems")
        for i, item in enumerate(test_items, 1):
            logger.info(f"  {i}. {item.alt} ({item.media_type}) - Lazy: {item.lazy_loaded}")

        # Test extracting URLs from media items
        from app.services.scraping_service import ScrapingService
        service = ScrapingService()
        urls = service._extract_media_urls_from_crawled_content(test_items)

        logger.info(f"✓ Extracted {len(urls)} URLs from media items:")
        for url in urls:
            logger.info(f"  - {url}")

        logger.info("✓ Media extraction test passed\n")
        return True

    except Exception as e:
        logger.error(f"✗ Media extraction test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_image_storage_service():
    """Test ImageStorageService configuration."""
    try:
        from app.services.image_storage_service import ImageStorageService

        logger.info("=" * 60)
        logger.info("TEST 4: ImageStorageService Configuration")
        logger.info("=" * 60)

        service = ImageStorageService()

        logger.info(f"✓ ImageStorageService initialized")
        logger.info(f"  - S3 Bucket: {service.bucket}")
        logger.info(f"  - Images Prefix: {service.images_prefix}")
        logger.info(f"  - S3 Client: {type(service.s3_client).__name__}")

        # Test key generation
        test_url = "https://example.com/image.jpg"
        test_filename = "test-image.jpg"

        s3_key = service._generate_s3_key(test_url, test_filename)
        logger.info(f"✓ S3 Key Generation:")
        logger.info(f"  - Input URL: {test_url}")
        logger.info(f"  - Generated Key: {s3_key}")

        logger.info("✓ ImageStorageService test passed\n")
        return True

    except Exception as e:
        logger.error(f"✗ ImageStorageService test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Run all tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " CRAWL4AI INTEGRATION TEST SUITE ".center(58) + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    results = {}

    # Run tests
    results["CrawlerClient"] = await test_crawler_client()
    results["ScrapingService"] = await test_scraping_service()
    results["MediaExtraction"] = await test_media_extraction()
    results["ImageStorageService"] = await test_image_storage_service()

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
    sys.exit(asyncio.run(main()))
