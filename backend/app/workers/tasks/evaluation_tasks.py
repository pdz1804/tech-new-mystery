"""Celery tasks for article evaluation and auto-review queue processing."""

import asyncio
import logging
import numpy as np
from typing import Optional, List

from app.workers.celery_app import celery_app
from app.repositories.article_repository import ArticleRepository
from app.repositories.pending_search_repository import PendingSearchRepository
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.services.article_service import ArticleService
from app.services.evaluation_service import EvaluationService
from app.services.evaluation_pipeline import EvaluationPipeline
from app.models.clustering import ClusteringEvaluationModel
from app.config import settings
from app.utils.time import now_timestamp
from time import time as timestamp
from datetime import datetime

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def evaluate_article_task(self, article_id: str) -> dict:
    """Evaluate a single article's quality score.

    Args:
        article_id: Article ID to evaluate

    Returns:
        Result dict with success status and score
    """
    try:
        result = asyncio.run(_evaluate_article(article_id))
        return result
    except Exception as exc:
        logger.error(f"[EVALUATE_ARTICLE] Task failed for {article_id}: {str(exc)}")
        raise self.retry(exc=exc)


async def _evaluate_article(article_id: str) -> dict:
    """Async helper: evaluate article and save score."""
    try:
        logger.info(f"[EVALUATE_ARTICLE] Starting evaluation for {article_id}")

        eval_service = EvaluationService()
        score = await eval_service.evaluate_article(article_id)

        if score is not None:
            logger.info(f"[EVALUATE_ARTICLE] Success: article={article_id}, score={score}")
            return {
                "success": True,
                "article_id": article_id,
                "quality_score": score,
            }
        else:
            logger.warning(f"[EVALUATE_ARTICLE] Failed to extract score for {article_id}")
            return {
                "success": False,
                "article_id": article_id,
                "quality_score": None,
                "error": "Failed to extract quality score",
            }
    except Exception as e:
        logger.error(f"[EVALUATE_ARTICLE] Error in async helper: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, max_retries=0)
def auto_process_single_search(self, search_id: str) -> dict:
    """Process a single pending search: approve → evaluate → publish/reject.

    This is a worker task dispatched by auto_review_queue_task.

    Args:
        search_id: Search ID to process

    Returns:
        Result dict with processing outcome

    Note: max_retries=0 because Crawl4AI timeouts in worker environment indicate
    browser/network contention that retries won't fix. Better to fail fast and
    let queue dispatcher try again later when load is lower.
    """
    try:
        result = asyncio.run(_auto_process_single_search(search_id))
        if not result.get("success"):
            logger.warning(f"[AUTO_PROCESS_SEARCH] Task failed for {search_id}: {result}")
        return result
    except Exception as exc:
        # Don't retry - log and return failure
        logger.error(
            f"[AUTO_PROCESS_SEARCH] Failed for {search_id}: {type(exc).__name__}: {str(exc)}",
            exc_info=True
        )
        # Return error as result instead of raising (no retry)
        return {
            "success": False,
            "search_id": search_id,
            "error": f"Task failed: {str(exc)}",
            "action": "rejected",
        }


async def _auto_process_single_search(search_id: str) -> dict:
    """Async helper: approve search, evaluate article, publish or reject."""
    try:
        logger.info(f"[AUTO_PROCESS_SEARCH] Starting for search {search_id}")

        # Fetch the pending search
        search_repo = PendingSearchRepository()
        search = await search_repo.get_by_id(search_id)

        if not search:
            logger.warning(f"[AUTO_PROCESS_SEARCH] Search not found: {search_id}")
            return {"success": False, "search_id": search_id, "error": "Search not found"}

        if search.status != "pending":
            logger.info(f"[AUTO_PROCESS_SEARCH] Search already {search.status}: {search_id}")
            return {"success": False, "search_id": search_id, "error": f"Search is {search.status}"}

        logger.info(f"[AUTO_PROCESS_SEARCH] Creating article from {search.url}")

        # Create article from search URL
        try:
            article_service = ArticleService(ArticleRepository())
            article = await article_service.create_from_url(
                url=search.url,
                title=search.title,
                auto_summarize=True,
            )

            article_id = article.get("article_id")
            logger.info(f"[AUTO_PROCESS_SEARCH] Article created: {article_id}")

        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"[AUTO_PROCESS_SEARCH] Validation error: {error_msg}")

            # Handle duplicate URL
            if "already exists" in error_msg:
                await search_repo.update_status(search_id, "rejected", approved_by="system")
                return {
                    "success": False,
                    "search_id": search_id,
                    "error": "Article already exists",
                    "action": "rejected",
                }

            await search_repo.update_status(search_id, "rejected", approved_by="system")
            return {
                "success": False,
                "search_id": search_id,
                "error": error_msg,
                "action": "rejected",
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AUTO_PROCESS_SEARCH] Error creating article: {error_msg}")

            # Auto-reject on scraping/crawl failures
            if any(x in error_msg.lower() for x in ["scraping", "crawl", "blocked"]):
                await search_repo.update_status(search_id, "rejected", approved_by="system")
                return {
                    "success": False,
                    "search_id": search_id,
                    "error": f"Scraping failed: {error_msg}",
                    "action": "rejected",
                }

            raise

        # Evaluate article and get threshold
        quality_score = article.get("quality_score")
        if quality_score is None:
            quality_score = 0.0
            logger.warning(f"[AUTO_PROCESS_SEARCH] No quality_score in article, using 0.0")

        settings_repo = SystemSettingsRepository()
        threshold = await settings_repo.get_threshold()
        logger.info(f"[AUTO_PROCESS_SEARCH] Quality score: {quality_score}, Threshold: {threshold}")

        # Decide: publish or reject
        if quality_score >= threshold:
            # Publish the article
            article_repo = ArticleRepository()
            await article_repo.update(
                article_id,
                is_published=True,
                published_at=now_timestamp(),
            )
            await search_repo.update_status(search_id, "approved", approved_by="auto-review")

            logger.info(f"[AUTO_PROCESS_SEARCH] Article PUBLISHED: {article_id}")
            return {
                "success": True,
                "search_id": search_id,
                "article_id": article_id,
                "quality_score": quality_score,
                "action": "published",
            }
        else:
            # Reject and delete article
            article_repo = ArticleRepository()
            await article_repo.delete(article_id)
            await search_repo.update_status(search_id, "rejected", approved_by="system")

            logger.info(f"[AUTO_PROCESS_SEARCH] Article REJECTED (low score): {article_id}")
            return {
                "success": False,
                "search_id": search_id,
                "article_id": article_id,
                "quality_score": quality_score,
                "threshold": threshold,
                "action": "rejected",
                "reason": f"Score {quality_score} < threshold {threshold}",
            }

    except Exception as e:
        logger.error(f"[AUTO_PROCESS_SEARCH] Error in async helper: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def auto_review_queue_task(self) -> dict:
    """Master task: fetch all pending searches and dispatch worker tasks.

    Dispatches all pending searches as worker tasks to be processed asynchronously.
    Does not re-trigger - one dispatch per invocation.

    Returns:
        Result dict with dispatch count
    """
    try:
        result = asyncio.run(_auto_review_queue())
        return result
    except Exception as exc:
        logger.error(f"[AUTO_REVIEW_QUEUE] Task failed: {str(exc)}")
        raise self.retry(exc=exc)


async def _auto_review_queue() -> dict:
    """Async helper: dispatch worker tasks for all pending searches in batches."""
    try:
        logger.info("[AUTO_REVIEW_QUEUE] Starting auto-review of queue")

        search_repo = PendingSearchRepository()
        pending = await search_repo.list_pending(limit=1000)

        logger.info(f"[AUTO_REVIEW_QUEUE] Found {len(pending)} pending searches")

        if not pending:
            return {"success": True, "total_pending": 0, "dispatched": 0, "total_batches": 0}

        # Batch configuration: optimize for 2GB memory upgrade + per-worker crawler init
        # Increased batch size (10→20) and reduced delay (5→3s) for faster queue drain
        # With 2GB memory, can safely handle 20 items per batch
        # Per-worker init eliminates browser contention, allowing tighter batching
        BATCH_SIZE = 20
        BATCH_DELAY_SECONDS = 3

        # Dispatch worker tasks in batches to prevent queue flooding
        dispatched_ids = []
        total_batches = (len(pending) - 1) // BATCH_SIZE + 1

        for batch_num, batch_start in enumerate(range(0, len(pending), BATCH_SIZE)):
            batch = pending[batch_start : batch_start + BATCH_SIZE]
            batch_dispatched = 0

            logger.info(f"[AUTO_REVIEW_QUEUE] Processing batch {batch_num + 1}/{total_batches} ({len(batch)} items)")

            for search in batch:
                try:
                    task = auto_process_single_search.delay(search.search_id)
                    dispatched_ids.append(search.search_id)
                    batch_dispatched += 1
                    logger.debug(f"[AUTO_REVIEW_QUEUE] Dispatched worker for {search.search_id}")
                except Exception as e:
                    logger.warning(f"[AUTO_REVIEW_QUEUE] Failed to dispatch {search.search_id}: {str(e)}")

            logger.info(f"[AUTO_REVIEW_QUEUE] Batch {batch_num + 1}: dispatched {batch_dispatched} items")

            # Add delay between batches to prevent queue flood (except after last batch)
            if batch_start + BATCH_SIZE < len(pending):
                logger.info(f"[AUTO_REVIEW_QUEUE] Waiting {BATCH_DELAY_SECONDS}s before next batch...")
                await asyncio.sleep(BATCH_DELAY_SECONDS)

        logger.info(f"[AUTO_REVIEW_QUEUE] Completed: Dispatched {len(dispatched_ids)} total items in {total_batches} batches")

        return {
            "success": True,
            "total_pending": len(pending),
            "dispatched": len(dispatched_ids),
            "batch_size": BATCH_SIZE,
            "total_batches": total_batches,
        }

    except Exception as e:
        logger.error(f"[AUTO_REVIEW_QUEUE] Error in async helper: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, max_retries=1, default_retry_delay=120)
def backfill_quality_scores_task(self) -> dict:
    """Backfill quality scores for articles that don't have them yet.

    Scans all articles and dispatches evaluation tasks for those with no score.

    Returns:
        Result dict with dispatch count
    """
    try:
        result = asyncio.run(_backfill_quality_scores())
        return result
    except Exception as exc:
        logger.error(f"[BACKFILL_SCORES] Task failed: {str(exc)}")
        raise self.retry(exc=exc)


async def _backfill_quality_scores() -> dict:
    """Async helper: find articles without scores and dispatch evaluation tasks."""
    try:
        logger.info("[BACKFILL_SCORES] Starting quality score backfill")

        article_repo = ArticleRepository()
        articles, _ = await article_repo.list_all(limit=10000)

        logger.info(f"[BACKFILL_SCORES] Found {len(articles)} total articles")

        # Find articles without quality_score
        needs_eval = [
            a for a in articles
            if getattr(a, "quality_score", None) is None
        ]

        logger.info(f"[BACKFILL_SCORES] {len(needs_eval)} articles need evaluation")

        # Dispatch evaluation task for each
        dispatched_ids = []
        for article in needs_eval:
            try:
                task = evaluate_article_task.delay(article.article_id)
                dispatched_ids.append(article.article_id)
                logger.debug(f"[BACKFILL_SCORES] Dispatched evaluation for {article.article_id}")
            except Exception as e:
                logger.warning(f"[BACKFILL_SCORES] Failed to dispatch {article.article_id}: {str(e)}")

        logger.info(f"[BACKFILL_SCORES] Dispatched {len(dispatched_ids)} evaluation tasks")

        return {
            "success": True,
            "total_articles": len(articles),
            "needs_evaluation": len(needs_eval),
            "dispatched": len(dispatched_ids),
        }

    except Exception as e:
        logger.error(f"[BACKFILL_SCORES] Error in async helper: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, max_retries=1, default_retry_delay=120)
def backfill_quality_scores_force_task(self) -> dict:
    """Force backfill quality scores for ALL articles, re-evaluating existing ones.

    Returns:
        Result dict with dispatch count
    """
    try:
        result = asyncio.run(_backfill_quality_scores_force())
        return result
    except Exception as exc:
        logger.error(f"[BACKFILL_SCORES_FORCE] Task failed: {str(exc)}")
        raise self.retry(exc=exc)


async def _backfill_quality_scores_force() -> dict:
    """Async helper: re-evaluate ALL articles regardless of existing scores."""
    try:
        logger.info("[BACKFILL_SCORES_FORCE] Starting force quality score backfill")

        article_repo = ArticleRepository()
        articles, _ = await article_repo.list_all(limit=10000)

        logger.info(f"[BACKFILL_SCORES_FORCE] Found {len(articles)} total articles")

        # Force evaluation of ALL articles (don't filter by score)
        logger.info(f"[BACKFILL_SCORES_FORCE] Force re-evaluating all {len(articles)} articles")

        # Dispatch evaluation task for each
        dispatched_ids = []
        for article in articles:
            try:
                task = evaluate_article_task.delay(article.article_id)
                dispatched_ids.append(article.article_id)
                logger.debug(f"[BACKFILL_SCORES_FORCE] Dispatched evaluation for {article.article_id}")
            except Exception as e:
                logger.warning(f"[BACKFILL_SCORES_FORCE] Failed to dispatch {article.article_id}: {str(e)}")

        logger.info(f"[BACKFILL_SCORES_FORCE] Dispatched {len(dispatched_ids)} evaluation tasks")

        return {
            "success": True,
            "total_articles": len(articles),
            "dispatched": len(dispatched_ids),
        }

    except Exception as e:
        logger.error(f"[BACKFILL_SCORES_FORCE] Error in async helper: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    name="tasks.evaluate_clustering_quality",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def evaluate_clustering_quality(
    self,
    embeddings: List[List[float]],
    article_ids: List[str],
    num_articles: int,
    evaluation_type: str = "scheduled",
) -> dict:
    """
    Evaluate clustering quality across k values and select optimal k.

    Triggered after cluster_articles task completes.
    Calculates Silhouette Score, Davies-Bouldin Index, and Calinski-Harabasz Index
    for each k in [k_min, k_max] using weighted composite scoring.

    Args:
        embeddings: List of embeddings (1536 dims each) for all articles
        article_ids: List of article IDs in matching order
        num_articles: Total count of articles evaluated
        evaluation_type: "scheduled" or "manual" (default "scheduled")

    Returns:
        dict: Evaluation results with selected k_value and metrics
    """
    try:
        result = asyncio.run(_evaluate_clustering_quality_async(
            embeddings=embeddings,
            article_ids=article_ids,
            num_articles=num_articles,
            evaluation_type=evaluation_type,
        ))
        logger.info(f"[EVALUATE_CLUSTERING] Task completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"[EVALUATE_CLUSTERING] Task failed: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc)


async def _evaluate_clustering_quality_async(
    embeddings: List[List[float]],
    article_ids: List[str],
    num_articles: int,
    evaluation_type: str = "scheduled",
) -> dict:
    """
    Async helper: run evaluation pipeline and store results in DynamoDB.

    Args:
        embeddings: List of embedding vectors
        article_ids: List of article IDs
        num_articles: Total article count
        evaluation_type: "scheduled" or "manual"

    Returns:
        dict with evaluation_id and selected k_value
    """
    try:
        embeddings_count = len(embeddings)
        article_id_count = len(article_ids)
        if embeddings_count != article_id_count:
            logger.warning(
                "[EVALUATE_CLUSTERING] Input mismatch: %d embeddings for %d article IDs",
                embeddings_count,
                article_id_count,
            )

        articles_evaluated = min(embeddings_count, article_id_count)
        logger.info(
            f"[EVALUATE_CLUSTERING] Starting evaluation: "
            f"{embeddings_count} embeddings for {num_articles} requested articles "
            f"({articles_evaluated} evaluable)"
        )
        if articles_evaluated < 3:
            logger.error("[EVALUATE_CLUSTERING] Need at least 3 embeddings to evaluate clustering")
            return {
                "success": False,
                "error": "At least 3 embeddings are required",
                "articles_evaluated": articles_evaluated,
                "articles_requested": num_articles,
            }
        start_time = timestamp()

        # Convert embeddings to numpy array
        embeddings_array = np.array(embeddings[:articles_evaluated], dtype=np.float32)
        article_ids = article_ids[:articles_evaluated]

        # Initialize evaluation pipeline with admin-configured weights
        pipeline = EvaluationPipeline(
            silhouette_weight=settings.clustering_silhouette_weight,
            davies_bouldin_weight=settings.clustering_davies_bouldin_weight,
            calinski_harabasz_weight=settings.clustering_calinski_harabasz_weight,
        )

        logger.info(
            f"[EVALUATE_CLUSTERING] Using weights: "
            f"silhouette={settings.clustering_silhouette_weight}, "
            f"davies_bouldin={settings.clustering_davies_bouldin_weight}, "
            f"calinski_harabasz={settings.clustering_calinski_harabasz_weight}"
        )

        # Run evaluation pipeline
        results, summary = pipeline.evaluate_clustering(
            embeddings=embeddings_array,
            cluster_assignments={},  # Not used in k-means evaluation
            article_ids=article_ids,
            k_min=settings.clustering_k_min,
            k_max=settings.clustering_k_max,
        )

        if not results:
            logger.error("[EVALUATE_CLUSTERING] No evaluation results generated")
            return {
                "success": False,
                "error": "No evaluation results",
                "articles_evaluated": articles_evaluated,
                "articles_requested": num_articles,
            }

        # Generate evaluation ID
        now = now_timestamp()
        eval_id = f"eval-{datetime.utcfromtimestamp(now).strftime('%Y-%m-%d-%H-%M')}"
        logger.info(f"[EVALUATE_CLUSTERING] Generated evaluation_id: {eval_id}")

        # Prepare evaluation results for storage
        evaluation_results = [r.to_dict() for r in results]

        # Check quality threshold
        best_composite_score = summary["best_composite_score"]
        quality_threshold_met = (
            best_composite_score >= settings.clustering_quality_threshold
        )

        logger.info(
            f"[EVALUATE_CLUSTERING] Quality assessment: "
            f"best_composite_score={best_composite_score:.4f}, "
            f"threshold={settings.clustering_quality_threshold}, "
            f"met={quality_threshold_met}"
        )

        # Prepare metrics summary for DynamoDB storage
        metrics_summary_dict = {}
        if "metrics_summary" in summary:
            for metric_name, metric_stats in summary["metrics_summary"].items():
                metrics_summary_dict[metric_name] = metric_stats

        # Save evaluation results to DynamoDB
        now_ts = now_timestamp()
        ttl = now_ts + (settings.clustering_evaluation_ttl_days * 86400)

        # Convert evaluation results to proper format for DynamoDB
        eval_items = []
        for result_dict in evaluation_results:
            eval_items.append(result_dict)

        evaluation_model = ClusteringEvaluationModel(
            eval_id,
            run_timestamp=now,
            evaluation_type=evaluation_type,
            total_articles_evaluated=articles_evaluated,
            evaluation_results=eval_items,
            selected_k_value=summary["selected_k_value"],
            best_composite_score=best_composite_score,
            admin_weights={
                "silhouette_weight": settings.clustering_silhouette_weight,
                "davies_bouldin_weight": settings.clustering_davies_bouldin_weight,
                "calinski_harabasz_weight": settings.clustering_calinski_harabasz_weight,
            },
            quality_threshold_met=quality_threshold_met,
            metrics_summary=metrics_summary_dict,
            completed_at=now_timestamp(),
            ttl=ttl,
        )

        # Save to DynamoDB (run in thread to avoid blocking)
        await asyncio.to_thread(evaluation_model.save)
        logger.info(f"[EVALUATE_CLUSTERING] Saved evaluation results to DynamoDB: {eval_id}")

        # Queue clustering task to generate clusters with selected K
        selected_k = summary["selected_k_value"]
        logger.info(f"[EVALUATE_CLUSTERING] Queuing clustering task with K={selected_k}")

        from app.workers.tasks.clustering_tasks import cluster_articles
        cluster_articles.delay(
            embeddings=embeddings,
            article_ids=article_ids,
            k_value=selected_k,
            evaluation_id=eval_id,
        )

        duration = timestamp() - start_time

        return {
            "success": True,
            "evaluation_id": eval_id,
            "articles_evaluated": articles_evaluated,
            "articles_requested": num_articles,
            "selected_k_value": summary["selected_k_value"],
            "best_composite_score": best_composite_score,
            "quality_threshold_met": quality_threshold_met,
            "num_k_values_evaluated": len(results),
            "duration_seconds": duration,
        }

    except Exception as e:
        logger.error(
            f"[EVALUATE_CLUSTERING] Error in async helper: {str(e)}",
            exc_info=True
        )
        raise
