"""Cluster data repository for DynamoDB operations."""

import asyncio
import logging
from pynamodb.exceptions import DoesNotExist

from app.models.clustering import (
    ArticleClusterModel,
    ClusterMetadataModel,
)
from app.models.article import ArticleModel

logger = logging.getLogger(__name__)


class ClusterRepository:
    """Repository for cluster DynamoDB operations."""

    async def get_cluster_metadata(self, cluster_id: str) -> ClusterMetadataModel | None:
        """Get cluster metadata by cluster ID.

        Args:
            cluster_id (str): Cluster ID

        Returns:
            ClusterMetadataModel or None if not found
        """
        logger.debug(f"Fetching cluster metadata: {cluster_id}")
        try:
            cluster = await asyncio.to_thread(
                ClusterMetadataModel.get, cluster_id
            )
            logger.debug(f"Cluster metadata found: {cluster.label}")
            return cluster
        except DoesNotExist:
            logger.debug(f"Cluster metadata not found: {cluster_id}")
            return None
        except Exception as e:
            logger.error(
                f"Error fetching cluster {cluster_id}: {type(e).__name__}: {str(e)}"
            )
            raise

    async def list_cluster_metadata(
        self,
        limit: int = 20,
        last_key: str | None = None,
        sort_by: str = "size",
    ) -> tuple[list[ClusterMetadataModel], dict | None]:
        """List all cluster metadata with pagination.

        Args:
            limit (int): Maximum items per page (default 20)
            last_key (str): Pagination cursor for next page
            sort_by (str): Sort key - "size", "recency", or "diversity"

        Returns:
            Tuple of (clusters_list, next_last_key for pagination)
        """
        logger.debug(
            "Scanning cluster metadata: limit=%s, has_last_key=%s, sort_by=%s",
            limit,
            last_key is not None,
            sort_by,
        )
        try:
            results = await asyncio.to_thread(
                lambda: ClusterMetadataModel.scan(
                    limit=limit,
                    last_evaluated_key=last_key,
                )
            )
            clusters = list(results)
            logger.debug(f"Cluster metadata scan returned {len(clusters)} items")

            # Sort based on sort_by parameter
            if sort_by == "size":
                clusters.sort(key=lambda c: c.article_count, reverse=True)
            elif sort_by == "recency":
                clusters.sort(key=lambda c: c.updated_at, reverse=True)
            elif sort_by == "diversity":
                clusters.sort(key=lambda c: c.diversity_score, reverse=True)

            return clusters, results.last_evaluated_key
        except Exception as e:
            logger.error(
                f"Error scanning cluster metadata: {type(e).__name__}: {str(e)}"
            )
            raise

    async def get_articles_in_cluster(
        self,
        cluster_id: str,
        limit: int = 20,
        last_key: str | None = None,
    ) -> tuple[list[ArticleClusterModel], dict | None]:
        """Get articles in a cluster with pagination.

        Args:
            cluster_id (str): Cluster ID
            limit (int): Maximum items per page
            last_key (str): Pagination cursor

        Returns:
            Tuple of (articles_list, next_last_key)
        """
        logger.debug(
            "Fetching articles in cluster: cluster_id=%s, limit=%s",
            cluster_id,
            limit,
        )
        try:
            results = await asyncio.to_thread(
                lambda: ArticleClusterModel.query(
                    cluster_id,
                    limit=limit,
                    last_evaluated_key=last_key,
                )
            )
            articles = list(results)
            logger.debug(
                f"Cluster {cluster_id} query returned {len(articles)} article assignments"
            )
            return articles, results.last_evaluated_key
        except Exception as e:
            logger.error(
                f"Error querying articles in cluster {cluster_id}: {type(e).__name__}: {str(e)}"
            )
            raise

    async def get_article_cluster_assignment(
        self, article_id: str
    ) -> ArticleClusterModel | None:
        """Get cluster assignment for an article using GSI.

        Args:
            article_id (str): Article ID

        Returns:
            ArticleClusterModel or None if not found
        """
        logger.debug(f"Fetching cluster assignment for article: {article_id}")
        try:
            results = await asyncio.to_thread(
                lambda: list(ArticleClusterModel.article_id_index.query(
                    article_id, limit=1
                ))
            )
            if results:
                logger.debug(f"Article {article_id} found in cluster {results[0].cluster_id}")
                return results[0]
            else:
                logger.debug(f"No cluster assignment found for article: {article_id}")
                return None
        except Exception as e:
            logger.error(
                f"Error querying cluster assignment for {article_id}: {type(e).__name__}: {str(e)}"
            )
            raise

    async def get_articles_by_ids(
        self, article_ids: list[str]
    ) -> list[ArticleModel]:
        """Get multiple articles by IDs.

        Args:
            article_ids (list[str]): List of article IDs

        Returns:
            List of ArticleModel objects
        """
        logger.debug(f"Fetching {len(article_ids)} articles by ID")
        try:
            articles = await asyncio.to_thread(
                lambda: [
                    article for article in ArticleModel.batch_get(article_ids)
                ]
            )
            logger.debug(f"Retrieved {len(articles)} articles")
            return articles
        except Exception as e:
            logger.error(f"Error batch fetching articles: {type(e).__name__}: {str(e)}")
            raise

    async def count_clusters(self) -> int:
        """Count total clusters.

        Returns:
            Total number of clusters
        """
        logger.debug("Counting clusters")
        try:
            count = await asyncio.to_thread(
                lambda: ClusterMetadataModel.count()
            )
            logger.debug(f"Total clusters: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting clusters: {type(e).__name__}: {str(e)}")
            return 0

    async def get_trending_clusters(
        self, limit: int = 5
    ) -> list[ClusterMetadataModel]:
        """Get trending clusters (sorted by article count and recency).

        Args:
            limit (int): Maximum clusters to return (default 5)

        Returns:
            List of trending ClusterMetadataModel objects
        """
        logger.debug(f"Fetching trending clusters (limit={limit})")
        try:
            results = await asyncio.to_thread(
                lambda: list(ClusterMetadataModel.scan(limit=100))
            )

            # Sort by updated_at (recency) and then by article_count
            results.sort(
                key=lambda c: (c.updated_at, c.article_count),
                reverse=True
            )

            trending = results[:limit]
            logger.debug(f"Returning {len(trending)} trending clusters")
            return trending
        except Exception as e:
            logger.error(
                f"Error fetching trending clusters: {type(e).__name__}: {str(e)}"
            )
            raise
