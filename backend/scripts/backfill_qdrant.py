"""Backfill script to index all existing articles into Qdrant vector database.

This script:
1. Retrieves all articles from DynamoDB
2. Checks if each is already indexed in Qdrant
3. Generates embeddings for new articles
4. Batches indexing calls (10 per batch)
5. Logs progress and handles failures gracefully
6. Reports total success/failure counts

Usage:
    cd backend
    python -m scripts.backfill_qdrant
"""

import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def backfill_qdrant(force: bool = False):
    """Main backfill function."""
    try:
        from app.repositories.article_repository import ArticleRepository
        from app.services.qdrant_service import QdrantService

        logger.info("=" * 70)
        logger.info("QDRANT BACKFILL - Starting article indexing")
        if force:
            logger.info("Force mode enabled - existing Qdrant points will be upserted")
        logger.info("=" * 70)

        start_time = time.time()

        # Initialize services
        article_repo = ArticleRepository()
        qdrant_service = QdrantService()

        # Fetch all articles
        logger.info("Fetching all articles from DynamoDB...")
        articles, _ = await article_repo.list_all(limit=10000)

        if not articles:
            logger.warning("No articles found in database")
            return

        total = len(articles)
        logger.info(f"Found {total} articles to process")

        # Process articles in batches
        batch_size = 10
        indexed_count = 0
        skipped_count = 0
        failed_count = 0

        for batch_num in range(0, total, batch_size):
            batch = articles[batch_num : batch_num + batch_size]
            batch_num_display = (batch_num // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num_display}/{total_batches} "
                f"({len(batch)} articles)"
            )

            for i, article in enumerate(batch):
                article_num = batch_num + i + 1

                try:
                    exists = False
                    if not force:
                        # Check if article already indexed
                        exists = await qdrant_service.article_exists(article.article_id)

                    if exists:
                        logger.debug(
                            f"  [{article_num}/{total}] Article {article.article_id} "
                            f"already indexed - skipping"
                        )
                        skipped_count += 1
                        continue

                    # Index article
                    logger.debug(
                        f"  [{article_num}/{total}] Indexing article {article.article_id}: {article.title}"
                    )

                    success = await qdrant_service.index_article(
                        article_id=article.article_id,
                        slug=article.slug,
                        title=article.title,
                        summary=article.summary,
                        content=article.content,
                        category=article.category,
                        author=article.author,
                        published_at=article.published_at,
                        view_count=article.view_count,
                        source_id=article.source_id,
                    )

                    if success:
                        indexed_count += 1
                        logger.debug(f"  [{article_num}/{total}] Indexed: {article.title}")
                    else:
                        failed_count += 1
                        logger.warning(f"  [{article_num}/{total}] Failed to index: {article.title}")

                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"  [{article_num}/{total}] Error indexing {article.article_id}: {str(e)}"
                    )
                    continue

        # Final statistics
        elapsed_time = time.time() - start_time
        avg_per_article = elapsed_time / total if total > 0 else 0

        logger.info("=" * 70)
        logger.info("QDRANT BACKFILL - COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Total articles: {total}")
        logger.info(f"Indexed: {indexed_count}")
        logger.info(f"Skipped (already indexed): {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Total time: {elapsed_time:.1f}s")
        logger.info(f"Average per article: {avg_per_article*1000:.0f}ms")
        logger.info("=" * 70)

        # Get final stats
        stats = await qdrant_service.get_collection_stats()
        logger.info(f"Collection stats: {stats}")

        if failed_count > 0:
            logger.warning(f"Backfill completed with {failed_count} failures")
            return False

        logger.info("Backfill completed successfully!")
        return True

    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        logger.error("Make sure you're running this from the backend directory with virtual env activated")
        return False
    except Exception as e:
        logger.error(f"Backfill failed: {str(e)}", exc_info=True)
        return False


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Backfill article embeddings into Qdrant")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-upload embeddings for articles even if they already exist in Qdrant",
    )
    args = parser.parse_args()

    try:
        success = asyncio.run(backfill_qdrant(force=args.force))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("Backfill cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
