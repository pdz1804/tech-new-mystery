"""Repository for clustering evaluation DynamoDB operations."""

import asyncio
import logging
from typing import List, Optional

from pynamodb.exceptions import DoesNotExist

from app.models.clustering import ClusteringEvaluationModel

logger = logging.getLogger(__name__)


class ClusteringEvaluationRepository:
    """Repository for clustering evaluation DynamoDB operations."""

    async def get_evaluation_by_id(
        self, evaluation_id: str
    ) -> Optional[ClusteringEvaluationModel]:
        """Get clustering evaluation by evaluation_id.

        Args:
            evaluation_id (str): Evaluation ID (format: "eval-{YYYY-MM-DD}-{HH}-{MM}")

        Returns:
            ClusteringEvaluationModel or None if not found
        """
        logger.debug(f"Fetching evaluation: {evaluation_id}")
        try:
            evaluation = await asyncio.to_thread(
                ClusteringEvaluationModel.get, evaluation_id
            )
            logger.debug(f"Evaluation found: {evaluation.evaluation_id}")
            return evaluation
        except DoesNotExist:
            logger.debug(f"Evaluation not found: {evaluation_id}")
            return None
        except Exception as e:
            logger.error(
                f"Error fetching evaluation {evaluation_id}: {type(e).__name__}: {str(e)}"
            )
            raise

    async def get_latest_evaluations(
        self, limit: int = 5
    ) -> List[ClusteringEvaluationModel]:
        """Get latest N evaluations sorted by timestamp (newest first).

        Args:
            limit (int): Maximum number of evaluations to return (default 5, max 20)

        Returns:
            List of ClusteringEvaluationModel sorted by timestamp descending
        """
        logger.debug(f"Fetching latest {limit} evaluations")
        try:
            # Use scan and sort in memory; table volumes are small for 30-day
            # evaluation retention and this works in local/test DynamoDB too.
            results = await asyncio.to_thread(
                lambda: ClusteringEvaluationModel.scan(
                    limit=limit * 2,  # Fetch extra to account for filtering
                )
            )
            evaluations = list(results)

            # Sort by run_timestamp descending (newest first)
            evaluations.sort(key=lambda e: e.run_timestamp, reverse=True)

            # Return top N
            evaluations = evaluations[:limit]

            logger.debug(f"Retrieved {len(evaluations)} evaluations")
            return evaluations

        except Exception as e:
            logger.error(
                f"Error scanning evaluations: {type(e).__name__}: {str(e)}"
            )
            raise

    async def save_evaluation(
        self, evaluation: ClusteringEvaluationModel
    ) -> bool:
        """Save clustering evaluation to DynamoDB.

        Args:
            evaluation (ClusteringEvaluationModel): Evaluation object to save

        Returns:
            bool: True if saved successfully
        """
        logger.debug(f"Saving evaluation: {evaluation.evaluation_id}")
        try:
            await asyncio.to_thread(evaluation.save)
            logger.info(
                f"Evaluation saved: {evaluation.evaluation_id} "
                f"(k={evaluation.selected_k_value}, score={evaluation.best_composite_score:.3f})"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error saving evaluation {evaluation.evaluation_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise

    async def delete_evaluation(self, evaluation_id: str) -> bool:
        """Delete clustering evaluation from DynamoDB.

        Args:
            evaluation_id (str): Evaluation ID to delete

        Returns:
            bool: True if deleted successfully
        """
        logger.debug(f"Deleting evaluation: {evaluation_id}")
        try:
            evaluation = await self.get_evaluation_by_id(evaluation_id)
            if not evaluation:
                logger.warning(f"Evaluation not found for deletion: {evaluation_id}")
                return False

            await asyncio.to_thread(evaluation.delete)
            logger.info(f"Evaluation deleted: {evaluation_id}")
            return True
        except Exception as e:
            logger.error(
                f"Error deleting evaluation {evaluation_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise
