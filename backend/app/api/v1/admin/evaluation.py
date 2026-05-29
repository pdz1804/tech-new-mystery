"""Admin endpoints for querying and managing clustering evaluation results."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime

from app.api.dependencies import require_admin
from app.repositories.clustering_evaluation_repository import ClusteringEvaluationRepository
from app.repositories.clustering_config_repository import ClusteringConfigRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clustering/evaluations", tags=["admin-clustering-evaluations"])


# ============================================================
# Response Models
# ============================================================


class EvaluationResultItem(BaseModel):
    """Single evaluation result for a k value."""

    k_value: int
    silhouette_score: float
    davies_bouldin_index: float
    calinski_harabasz_index: float
    silhouette_rank: int
    davies_bouldin_rank: int
    calinski_harabasz_rank: int
    weighted_composite_score: float
    num_clusters_formed: int
    avg_cluster_size: float
    noise_percentage: float
    evaluation_time_ms: int


class EvaluationItem(BaseModel):
    """Single evaluation summary for list response."""

    evaluation_id: str
    timestamp: int
    evaluation_type: str
    num_articles: int
    num_clusters: int
    silhouette_score: float
    davies_bouldin_index: float
    calinski_harabasz_index: float
    weighted_score: float
    selected_k_value: int
    quality_threshold_met: bool


class PaginationInfo(BaseModel):
    """Pagination information."""

    total: int
    limit: int
    offset: int


class EvaluationsListResponse(BaseModel):
    """Response for evaluations list endpoint."""

    items: List[EvaluationItem]
    pagination: PaginationInfo


class MetricsSummaryItem(BaseModel):
    """Summary statistics for a single metric."""

    min: float
    max: float
    mean: float
    std_dev: float


class EvaluationDetailResponse(BaseModel):
    """Full evaluation details response."""

    evaluation_id: str
    timestamp: int
    evaluation_type: str
    total_articles_evaluated: int
    selected_k_value: int
    best_composite_score: float
    quality_threshold_met: bool
    completed_at: int
    admin_weights: Dict[str, float]
    evaluation_results: List[EvaluationResultItem]
    metrics_summary: Dict[str, Dict[str, float]]


class TriggerEvaluationRequest(BaseModel):
    """Request to manually trigger clustering evaluation."""

    trigger_reason: str = Field(..., min_length=1, max_length=200)


class TriggerEvaluationResponse(BaseModel):
    """Response for manual evaluation trigger."""

    job_id: str
    status: str


# ============================================================
# Endpoints
# ============================================================


@router.get("", response_model=EvaluationsListResponse)
async def list_evaluations(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: dict = Depends(require_admin),
) -> EvaluationsListResponse:
    """
    List clustering evaluations with pagination (admin only).

    Args:
        limit: Maximum number of evaluations to return (1-100, default 10)
        offset: Number of evaluations to skip (default 0)

    Returns:
        List of evaluations with pagination metadata
    """
    try:
        repo = ClusteringEvaluationRepository()
        logger.info(f"[EVAL_LIST] Fetching evaluations with limit={limit}, offset={offset}")

        # Get latest evaluations (scan all, then paginate in memory)
        # Note: In production with large datasets, add GSI for efficient pagination
        evaluations = await repo.get_latest_evaluations(limit=1000)

        # Calculate total before pagination
        total = len(evaluations)

        # Apply pagination
        paginated = evaluations[offset : offset + limit]

        # Convert to response items
        items = []
        for eval_model in paginated:
            # Get the best metric from evaluation_results (first element has best composite score)
            best_result = (
                eval_model.evaluation_results[0]
                if eval_model.evaluation_results
                else None
            )

            item = EvaluationItem(
                evaluation_id=eval_model.evaluation_id,
                timestamp=eval_model.timestamp,
                evaluation_type=eval_model.evaluation_type,
                num_articles=eval_model.total_articles_evaluated,
                num_clusters=eval_model.selected_k_value,
                silhouette_score=best_result.silhouette_score if best_result else 0.0,
                davies_bouldin_index=best_result.davies_bouldin_index if best_result else 0.0,
                calinski_harabasz_index=best_result.calinski_harabasz_index if best_result else 0.0,
                weighted_score=eval_model.best_composite_score,
                selected_k_value=eval_model.selected_k_value,
                quality_threshold_met=eval_model.quality_threshold_met,
            )
            items.append(item)

        logger.info(
            f"[EVAL_LIST] Retrieved {len(items)} evaluations (total={total}, offset={offset})"
        )

        return EvaluationsListResponse(
            items=items,
            pagination=PaginationInfo(total=total, limit=limit, offset=offset),
        )

    except Exception as e:
        logger.error(f"[EVAL_LIST] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list evaluations: {str(e)}")


@router.get("/{evaluation_id}", response_model=EvaluationDetailResponse)
async def get_evaluation_detail(
    evaluation_id: str,
    _: dict = Depends(require_admin),
) -> EvaluationDetailResponse:
    """
    Get full evaluation details including all metrics and results (admin only).

    Args:
        evaluation_id: Evaluation ID (format: "eval-{YYYY-MM-DD}-{HH}-{MM}")

    Returns:
        Complete evaluation details with all metrics and results

    Raises:
        HTTPException(404): If evaluation not found
        HTTPException(500): If database error occurs
    """
    try:
        repo = ClusteringEvaluationRepository()
        logger.info(f"[EVAL_DETAIL] Fetching evaluation: {evaluation_id}")

        eval_model = await repo.get_evaluation_by_id(evaluation_id)

        if not eval_model:
            logger.warning(f"[EVAL_DETAIL] Evaluation not found: {evaluation_id}")
            raise HTTPException(status_code=404, detail="Evaluation not found")

        # Convert evaluation results
        results = []
        for result_item in eval_model.evaluation_results:
            results.append(
                EvaluationResultItem(
                    k_value=result_item.k_value,
                    silhouette_score=result_item.silhouette_score,
                    davies_bouldin_index=result_item.davies_bouldin_index,
                    calinski_harabasz_index=result_item.calinski_harabasz_index,
                    silhouette_rank=result_item.silhouette_rank,
                    davies_bouldin_rank=result_item.davies_bouldin_rank,
                    calinski_harabasz_rank=result_item.calinski_harabasz_rank,
                    weighted_composite_score=result_item.weighted_composite_score,
                    num_clusters_formed=result_item.num_clusters_formed,
                    avg_cluster_size=result_item.avg_cluster_size,
                    noise_percentage=result_item.noise_percentage,
                    evaluation_time_ms=result_item.evaluation_time_ms,
                )
            )

        # Convert metrics summary
        metrics_summary_dict = {}
        if eval_model.metrics_summary:
            for metric_name, metric_stats in eval_model.metrics_summary.items():
                if isinstance(metric_stats, dict):
                    metrics_summary_dict[metric_name] = {
                        "min": metric_stats.get("min", 0.0),
                        "max": metric_stats.get("max", 0.0),
                        "mean": metric_stats.get("mean", 0.0),
                        "std_dev": metric_stats.get("std_dev", 0.0),
                    }

        # Convert admin weights
        admin_weights_dict = {}
        if eval_model.admin_weights:
            if isinstance(eval_model.admin_weights, dict):
                admin_weights_dict = eval_model.admin_weights
            else:
                # Handle case where admin_weights might be a MapAttribute
                admin_weights_dict = {
                    "silhouette_weight": getattr(eval_model.admin_weights, "silhouette_weight", 0.5),
                    "davies_bouldin_weight": getattr(eval_model.admin_weights, "davies_bouldin_weight", 0.3),
                    "calinski_harabasz_weight": getattr(eval_model.admin_weights, "calinski_harabasz_weight", 0.2),
                }

        logger.info(
            f"[EVAL_DETAIL] Retrieved evaluation {evaluation_id} "
            f"(k={eval_model.selected_k_value}, score={eval_model.best_composite_score:.3f})"
        )

        return EvaluationDetailResponse(
            evaluation_id=eval_model.evaluation_id,
            timestamp=eval_model.timestamp,
            evaluation_type=eval_model.evaluation_type,
            total_articles_evaluated=eval_model.total_articles_evaluated,
            selected_k_value=eval_model.selected_k_value,
            best_composite_score=eval_model.best_composite_score,
            quality_threshold_met=eval_model.quality_threshold_met,
            completed_at=eval_model.completed_at,
            admin_weights=admin_weights_dict,
            evaluation_results=results,
            metrics_summary=metrics_summary_dict,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EVAL_DETAIL] Error fetching evaluation {evaluation_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch evaluation: {str(e)}")


@router.delete("/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: str,
    _: dict = Depends(require_admin),
):
    """
    Delete clustering evaluation from DynamoDB (admin only).

    Args:
        evaluation_id: Evaluation ID to delete

    Returns:
        204 No Content on success

    Raises:
        HTTPException(404): If evaluation not found
        HTTPException(500): If database error occurs
    """
    try:
        repo = ClusteringEvaluationRepository()
        logger.warning(f"[EVAL_DELETE] Admin deleting evaluation: {evaluation_id}")

        deleted = await repo.delete_evaluation(evaluation_id)

        if not deleted:
            logger.warning(f"[EVAL_DELETE] Evaluation not found: {evaluation_id}")
            raise HTTPException(status_code=404, detail="Evaluation not found")

        logger.info(f"[EVAL_DELETE] Evaluation deleted: {evaluation_id}")

        # Return 204 No Content
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EVAL_DELETE] Error deleting evaluation {evaluation_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete evaluation: {str(e)}")


@router.post("/trigger", response_model=TriggerEvaluationResponse)
async def trigger_evaluation(
    request: TriggerEvaluationRequest,
    _: dict = Depends(require_admin),
) -> TriggerEvaluationResponse:
    """
    Manually trigger clustering evaluation (admin only).

    Queues a Celery task to run the clustering evaluation pipeline.
    Evaluation will process all articles and calculate clustering quality metrics.

    Args:
        request: TriggerEvaluationRequest with trigger_reason

    Returns:
        Job ID and status

    Raises:
        HTTPException(500): If task queueing fails
    """
    try:
        from app.workers.tasks.evaluation_tasks import evaluate_clustering_quality

        logger.warning(
            f"[EVAL_TRIGGER] Admin manually triggering clustering evaluation. "
            f"Reason: {request.trigger_reason}"
        )

        # Queue the evaluation task
        task = evaluate_clustering_quality.delay(trigger_reason=request.trigger_reason)

        logger.info(f"[EVAL_TRIGGER] Evaluation task queued with ID: {task.id}")

        return TriggerEvaluationResponse(
            job_id=task.id,
            status="queued",
        )

    except Exception as e:
        logger.error(f"[EVAL_TRIGGER] Error triggering evaluation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger evaluation: {str(e)}"
        )
