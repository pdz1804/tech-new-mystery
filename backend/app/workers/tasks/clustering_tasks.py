"""Celery tasks for article clustering with HDBSCAN."""

import logging
import asyncio
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from time import time as timestamp

from app.config import settings
from app.workers.celery_app import celery_app
from app.repositories.article_repository import ArticleRepository
from app.services.embedding_service import EmbeddingService
from app.services.clustering_engine import ClusteringEngine
from app.models.clustering import (
    ArticleClusterModel,
    ClusterMetadataModel,
    ArticleEmbeddingModel,
    TopArticleItem,
)
from app.utils.time import now_timestamp

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.cluster_articles",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min backoff
)
def cluster_articles(self):
    """
    Daily clustering job: 6am & 6pm UTC.

    - Fetch articles from last 7 days
    - Generate/retrieve embeddings
    - Run HDBSCAN clustering
    - Generate cluster metadata and labels
    - Store results in DynamoDB

    Returns:
        dict: Task result with clustering statistics
    """
    try:
        result = asyncio.run(_cluster_articles_async())
        logger.info(f"Clustering task completed successfully: {result}")
        return result
    except Exception as exc:
        logger.error(f"Clustering task failed: {exc}", exc_info=True)
        # Exponential backoff retry
        raise self.retry(exc=exc)


async def _cluster_articles_async() -> dict:
    """
    Internal async function to orchestrate clustering pipeline.

    Returns:
        dict: Statistics about clustering run
    """
    try:
        start_time = timestamp()
        logger.info("Starting clustering pipeline")

        # Step 1: Fetch recent articles (last 7 days)
        logger.info("Step 1: Fetching articles from last 7 days")
        article_repo = ArticleRepository()
        articles, _ = await article_repo.list_all(limit=10000)

        if not articles:
            logger.warning("No articles found for clustering")
            return {
                "success": True,
                "message": "No articles to cluster",
                "articles_count": 0,
                "clusters_count": 0,
                "duration_seconds": timestamp() - start_time,
            }

        logger.info(f"Found {len(articles)} articles for clustering")

        # Step 2: Get/generate embeddings
        logger.info("Step 2: Retrieving/generating embeddings")
        embedding_service = EmbeddingService()
        embeddings, article_ids = await _get_or_generate_embeddings(
            articles, embedding_service
        )

        if len(embeddings) == 0:
            logger.warning("No embeddings generated")
            return {
                "success": True,
                "message": "No embeddings available for clustering",
                "articles_count": len(articles),
                "clusters_count": 0,
                "duration_seconds": timestamp() - start_time,
            }

        logger.info(f"Retrieved embeddings for {len(embeddings)} articles")

        # Step 3: Run HDBSCAN clustering
        logger.info("Step 3: Running HDBSCAN clustering")
        clustering_engine = ClusteringEngine(
            min_cluster_size=settings.clustering_min_cluster_size,
            min_samples=settings.clustering_min_samples,
            metric="cosine",
        )

        embeddings_array = np.array(embeddings)
        cluster_assignments, stats = clustering_engine.cluster_articles(
            embeddings_array, article_ids
        )

        logger.info(
            f"Clustering complete: {stats['num_clusters']} clusters, "
            f"{stats['num_noise']} noise articles ({stats['noise_percent']:.1f}%)"
        )

        # Step 4: Generate cluster metadata and save results
        logger.info("Step 4: Generating cluster metadata and saving results")
        num_saved = await _save_clustering_results(
            cluster_assignments,
            stats,
            embeddings_array,
            article_ids,
            articles,
            article_repo,
        )

        duration = timestamp() - start_time
        logger.info(f"Clustering pipeline completed in {duration:.2f} seconds")

        result = {
            "success": True,
            "articles_count": len(articles),
            "embeddings_count": len(embeddings),
            "clusters_count": stats["num_clusters"],
            "noise_count": stats["num_noise"],
            "noise_percent": stats["noise_percent"],
            "cluster_assignments_saved": num_saved,
            "duration_seconds": duration,
        }

        # Step 5: Trigger evaluation pipeline (async)
        if settings.clustering_evaluation_enabled:
            logger.info("Triggering clustering evaluation pipeline")
            try:
                # Import here to avoid circular imports
                from app.workers.tasks.evaluation_tasks import evaluate_clustering_quality

                evaluate_clustering_quality.delay(
                    embeddings=[e for e in embeddings],
                    article_ids=article_ids,
                    num_articles=len(articles),
                )
                result["evaluation_triggered"] = True
            except Exception as e:
                logger.error(f"Failed to trigger evaluation pipeline: {e}")
                result["evaluation_triggered"] = False
        else:
            logger.info("Clustering evaluation disabled (clustering_evaluation_enabled=False)")
            result["evaluation_triggered"] = False

        return result

    except Exception as e:
        logger.error(f"Error in clustering pipeline: {e}", exc_info=True)
        raise


async def _get_or_generate_embeddings(
    articles: List,
    embedding_service: EmbeddingService
) -> tuple[List[List[float]], List[str]]:
    """
    Get cached embeddings or generate new ones for articles.

    Args:
        articles: List of article objects from repository
        embedding_service: EmbeddingService instance

    Returns:
        Tuple of (embeddings_list, article_ids_list)
    """
    embeddings = []
    article_ids = []
    articles_to_embed = []

    # Check cache for existing embeddings
    logger.debug(f"Checking embeddings cache for {len(articles)} articles")
    for article in articles:
        try:
            # Try to get cached embedding
            cached = await asyncio.to_thread(
                ArticleEmbeddingModel.get,
                article.article_id
            )
            embeddings.append(cached.embedding)
            article_ids.append(article.article_id)
            logger.debug(f"Using cached embedding for {article.article_id}")
        except:
            # Not in cache, will generate
            articles_to_embed.append(article)

    # Generate embeddings for articles not in cache
    if articles_to_embed:
        logger.info(f"Generating embeddings for {len(articles_to_embed)} new articles")

        batch_size = settings.openai_embedding_batch_size
        for i in range(0, len(articles_to_embed), batch_size):
            batch = articles_to_embed[i : i + batch_size]
            logger.info(f"Embedding batch {i // batch_size + 1}/{(len(articles_to_embed) + batch_size - 1) // batch_size}")

            for article in batch:
                try:
                    # Prepare text for embedding (title + summary)
                    text = f"{article.title or ''} {article.summary or ''}"
                    if not text.strip():
                        logger.warning(f"No text to embed for article {article.article_id}")
                        continue

                    embedding = await embedding_service.generate_embedding(text)

                    # Save to cache
                    now = now_timestamp()
                    ttl = now + (settings.clustering_ttl_days * 86400)

                    embedding_obj = ArticleEmbeddingModel(
                        article.article_id,
                        embedding=embedding,
                        embedding_model=settings.openai_embedding_model,
                        generated_at=now,
                        ttl=ttl,
                    )

                    await asyncio.to_thread(embedding_obj.save)
                    logger.debug(f"Cached embedding for {article.article_id}")

                    embeddings.append(embedding)
                    article_ids.append(article.article_id)

                except Exception as e:
                    logger.error(f"Failed to generate embedding for {article.article_id}: {e}")
                    continue

    logger.info(f"Total embeddings available: {len(embeddings)}/{len(articles)}")
    return embeddings, article_ids


async def _save_clustering_results(
    cluster_assignments: Dict[str, int],
    stats: Dict,
    embeddings_array: np.ndarray,
    article_ids: List[str],
    articles: List,
    article_repo: ArticleRepository,
) -> int:
    """
    Save clustering results to DynamoDB.

    Args:
        cluster_assignments: Dict[article_id, cluster_id]
        stats: Clustering statistics
        embeddings_array: Full embeddings array
        article_ids: Ordered list of article IDs
        articles: Original article objects
        article_repo: Article repository for lookups

    Returns:
        Number of assignments saved
    """
    now = now_timestamp()
    ttl = now + (settings.clustering_ttl_days * 86400)

    # Create mapping of article_id to article object
    article_map = {a.article_id: a for a in articles}

    # Track which cluster_ids we've processed (for metadata)
    clusters_metadata: Dict[str, dict] = {}

    # Save article cluster assignments
    logger.info("Saving article cluster assignments to DynamoDB")
    saved_count = 0

    for article_id, cluster_id in cluster_assignments.items():
        try:
            # Skip noise articles (cluster_id = -1) for now
            # They can be queried separately if needed
            if cluster_id == -1:
                continue

            # Calculate confidence score (distance from centroid)
            article_idx = article_ids.index(article_id)
            confidence = _calculate_confidence_score(
                embeddings_array[article_idx],
                embeddings_array,
                cluster_assignments,
                cluster_id,
            )

            # Create cluster ID with timestamp
            cluster_label = f"cluster-{datetime.utcnow().strftime('%Y%m%d')}-{cluster_id:03d}"

            # Save to DynamoDB
            assignment = ArticleClusterModel(
                cluster_label,
                article_id,
                assigned_at=now,
                confidence_score=confidence,
                ttl=ttl,
            )

            await asyncio.to_thread(assignment.save)
            saved_count += 1

            # Collect for metadata generation
            if cluster_label not in clusters_metadata:
                clusters_metadata[cluster_label] = {
                    "cluster_id": cluster_label,
                    "article_ids": [],
                    "confidences": [],
                }

            clusters_metadata[cluster_label]["article_ids"].append(article_id)
            clusters_metadata[cluster_label]["confidences"].append(confidence)

        except Exception as e:
            logger.error(f"Failed to save cluster assignment for {article_id}: {e}")
            continue

    logger.info(f"Saved {saved_count} cluster assignments")

    # Generate and save cluster metadata
    logger.info(f"Generating metadata for {len(clusters_metadata)} clusters")
    for cluster_label, cluster_data in clusters_metadata.items():
        try:
            await _generate_and_save_cluster_metadata(
                cluster_label,
                cluster_data,
                article_map,
                embeddings_array,
                article_ids,
                now,
                ttl,
            )
        except Exception as e:
            logger.error(f"Failed to generate metadata for {cluster_label}: {e}")
            continue

    return saved_count


def _calculate_confidence_score(
    article_embedding: np.ndarray,
    all_embeddings: np.ndarray,
    cluster_assignments: Dict[str, int],
    cluster_id: int,
) -> float:
    """
    Calculate confidence score as 1 - (normalized distance from centroid).

    Args:
        article_embedding: Single article embedding
        all_embeddings: All embeddings array
        cluster_assignments: Cluster assignments dict
        cluster_id: Target cluster ID

    Returns:
        Confidence score 0-1
    """
    try:
        # Get indices of articles in this cluster
        article_ids_for_cluster = [
            aid for aid, cid in cluster_assignments.items()
            if cid == cluster_id
        ]

        if not article_ids_for_cluster:
            return 0.0

        # Calculate centroid
        cluster_indices = []
        for i, aid in enumerate(cluster_assignments.keys()):
            if cluster_assignments[aid] == cluster_id:
                cluster_indices.append(i)

        if not cluster_indices:
            return 0.0

        cluster_embeddings = all_embeddings[cluster_indices]
        centroid = np.mean(cluster_embeddings, axis=0)

        # Calculate euclidean distance from centroid
        distance = np.linalg.norm(article_embedding - centroid)

        # Normalize distance (max distance ~ 2 for unit vectors in high dimensions)
        max_distance = 2.0
        normalized_distance = min(distance / max_distance, 1.0)

        # Confidence = 1 - normalized_distance
        confidence = max(0.0, 1.0 - normalized_distance)

        return float(confidence)

    except Exception as e:
        logger.warning(f"Failed to calculate confidence score: {e}")
        return 0.5  # Default to neutral confidence


async def _generate_and_save_cluster_metadata(
    cluster_label: str,
    cluster_data: dict,
    article_map: dict,
    embeddings_array: np.ndarray,
    article_ids: List[str],
    now: int,
    ttl: int,
) -> None:
    """
    Generate metadata for a cluster and save to DynamoDB.

    Args:
        cluster_label: Cluster identifier
        cluster_data: Dict with article_ids and confidences
        article_map: Dict[article_id, article_object]
        embeddings_array: Full embeddings array
        article_ids: Ordered list of article IDs
        now: Current timestamp
        ttl: TTL timestamp
    """
    article_ids_in_cluster = cluster_data["article_ids"]

    if not article_ids_in_cluster:
        logger.warning(f"No articles in cluster {cluster_label}")
        return

    logger.info(f"Generating metadata for {cluster_label} ({len(article_ids_in_cluster)} articles)")

    # Get articles for this cluster
    cluster_articles = [
        article_map[aid] for aid in article_ids_in_cluster
        if aid in article_map
    ]

    # Extract keywords using TF-IDF
    keywords = await _extract_keywords_tfidf(cluster_articles)
    logger.debug(f"Keywords for {cluster_label}: {keywords}")

    # Generate label via Claude Bedrock
    label = await _generate_cluster_label(keywords, cluster_articles)
    description = await _generate_cluster_description(label, keywords, cluster_articles)

    # Calculate diversity score (average pairwise cosine distance)
    diversity = await _calculate_diversity_score(
        article_ids_in_cluster,
        embeddings_array,
        article_ids,
    )

    # Calculate centroid embedding
    centroid = await _calculate_centroid_embedding(
        article_ids_in_cluster,
        embeddings_array,
        article_ids,
    )

    # Get top articles by engagement
    top_articles = await _get_top_articles(cluster_articles)

    # Determine size category
    size = len(article_ids_in_cluster)
    if size < 11:
        size_category = "SMALL"
    elif size < 51:
        size_category = "MEDIUM"
    else:
        size_category = "LARGE"

    # Save metadata
    metadata = ClusterMetadataModel(
        cluster_label,
        label=label,
        keywords=keywords,
        description=description,
        article_count=len(article_ids_in_cluster),
        size_category=size_category,
        diversity_score=diversity,
        centroid_embedding=centroid,
        top_articles=top_articles,
        created_at=now,
        updated_at=now,
        ttl=ttl,
    )

    try:
        await asyncio.to_thread(metadata.save)
        logger.info(f"Saved metadata for {cluster_label}")
    except Exception as e:
        logger.error(f"Failed to save metadata for {cluster_label}: {e}")
        raise


async def _extract_keywords_tfidf(articles: List) -> List[str]:
    """
    Extract top 5 keywords from articles using simple TF-IDF.

    Args:
        articles: List of article objects with titles and summaries

    Returns:
        List of top 5 keywords
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        # Prepare documents
        texts = []
        for article in articles:
            text = f"{article.title or ''} {article.summary or ''}"
            if text.strip():
                texts.append(text)

        if not texts:
            logger.warning("No text available for TF-IDF extraction")
            return ["article"] * 5  # Fallback

        # Calculate TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words="english",
            min_df=1,
            max_df=0.95,
        )

        vectorizer.fit(texts)
        feature_names = vectorizer.get_feature_names_out()

        # Get mean TF-IDF scores
        tfidf_matrix = vectorizer.transform(texts)
        scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

        # Get top 5 keywords
        top_indices = np.argsort(scores)[-5:][::-1]
        keywords = [feature_names[i].capitalize() for i in top_indices]

        logger.debug(f"Extracted keywords: {keywords}")
        return keywords

    except Exception as e:
        logger.error(f"Failed to extract keywords: {e}")
        return ["Technology", "News", "Article", "Content", "Topic"]


async def _generate_cluster_label(keywords: List[str], articles: List) -> str:
    """
    Generate cluster label using Claude Bedrock.

    Args:
        keywords: List of keywords for the cluster
        articles: List of articles in the cluster

    Returns:
        Generated cluster label
    """
    try:
        from app.integrations.llm_client import get_llm_client

        # Build prompt
        sample_titles = " | ".join([a.title or "" for a in articles[:3]])

        prompt = f"""Generate a concise, professional cluster label (3-6 words) for news articles with these characteristics:

Keywords: {", ".join(keywords)}
Sample titles: {sample_titles}

Return ONLY the label text, no quotes or explanation."""

        llm_client = await get_llm_client()

        label = await llm_client.generate(
            prompt=prompt,
            max_tokens=50,
            temperature=0.7,
        )

        label = label.strip().strip('"').strip("'")
        if not label:
            label = " & ".join(keywords[:2])

        logger.debug(f"Generated label: {label}")
        return label[:100]  # Truncate to 100 chars

    except Exception as e:
        logger.error(f"Failed to generate cluster label: {e}")
        # Fallback: combine top 2 keywords
        return " & ".join(keywords[:2])


async def _generate_cluster_description(label: str, keywords: List[str], articles: List) -> str:
    """
    Generate cluster description using Claude Bedrock.

    Args:
        label: Cluster label
        keywords: List of keywords
        articles: List of articles

    Returns:
        Generated description
    """
    try:
        from app.integrations.llm_client import get_llm_client

        # Build prompt
        sample_titles = " | ".join([a.title or "" for a in articles[:3]])

        prompt = f"""Generate a 1-2 sentence description for a news cluster:

Label: {label}
Keywords: {", ".join(keywords)}
Sample articles: {sample_titles}

Return ONLY the description text, no quotes or explanation."""

        llm_client = await get_llm_client()

        description = await llm_client.generate(
            prompt=prompt,
            max_tokens=100,
            temperature=0.7,
        )

        description = description.strip().strip('"').strip("'")
        if not description:
            description = f"Collection of articles related to {label.lower()}"

        logger.debug(f"Generated description: {description}")
        return description[:500]  # Truncate to 500 chars

    except Exception as e:
        logger.error(f"Failed to generate cluster description: {e}")
        return f"Collection of articles related to {label.lower()}"


async def _calculate_diversity_score(
    article_ids: List[str],
    embeddings_array: np.ndarray,
    all_article_ids: List[str],
) -> float:
    """
    Calculate diversity score as average pairwise cosine distance.

    Args:
        article_ids: Articles in this cluster
        embeddings_array: Full embeddings array
        all_article_ids: All article IDs (for indexing)

    Returns:
        Diversity score 0-1
    """
    try:
        if len(article_ids) < 2:
            return 0.5  # Default for single articles

        # Get indices for this cluster
        indices = [all_article_ids.index(aid) for aid in article_ids]
        cluster_embeddings = embeddings_array[indices]

        # Calculate pairwise cosine distances
        from sklearn.metrics.pairwise import cosine_distances

        distances = cosine_distances(cluster_embeddings)

        # Get mean distance (excluding diagonal)
        mask = np.ones(distances.shape, dtype=bool)
        np.fill_diagonal(mask, False)
        mean_distance = distances[mask].mean()

        # Normalize to 0-1 range
        diversity = min(mean_distance, 1.0)

        logger.debug(f"Diversity score: {diversity:.2f}")
        return float(diversity)

    except Exception as e:
        logger.error(f"Failed to calculate diversity score: {e}")
        return 0.5  # Default


async def _calculate_centroid_embedding(
    article_ids: List[str],
    embeddings_array: np.ndarray,
    all_article_ids: List[str],
) -> List[float]:
    """
    Calculate centroid embedding as mean of cluster embeddings.

    Args:
        article_ids: Articles in this cluster
        embeddings_array: Full embeddings array
        all_article_ids: All article IDs (for indexing)

    Returns:
        Centroid embedding (1536 dims)
    """
    try:
        if not article_ids:
            return [0.0] * 1536

        # Get indices for this cluster
        indices = [all_article_ids.index(aid) for aid in article_ids]
        cluster_embeddings = embeddings_array[indices]

        # Calculate centroid
        centroid = np.mean(cluster_embeddings, axis=0)

        return centroid.tolist()

    except Exception as e:
        logger.error(f"Failed to calculate centroid embedding: {e}")
        return [0.0] * 1536


async def _get_top_articles(articles: List, limit: int = 10) -> List[TopArticleItem]:
    """
    Get top articles by engagement score.

    Args:
        articles: List of article objects
        limit: Maximum number of articles to return

    Returns:
        List of TopArticleItem objects
    """
    try:
        # Sort by engagement score (or quality_score as fallback)
        sorted_articles = sorted(
            articles,
            key=lambda a: getattr(a, "engagement_score", 0) or getattr(a, "quality_score", 0),
            reverse=True,
        )

        top_items = []
        for article in sorted_articles[:limit]:
            engagement = getattr(article, "engagement_score", 0) or 0
            item = TopArticleItem(
                article_id=article.article_id,
                title=article.title or "Untitled",
                engagement_score=engagement,
            )
            top_items.append(item)

        logger.debug(f"Selected {len(top_items)} top articles")
        return top_items

    except Exception as e:
        logger.error(f"Failed to get top articles: {e}")
        return []
