"""Repository for system-wide settings."""

import asyncio
import logging
import time
from typing import Optional

from pynamodb.exceptions import DoesNotExist

from app.models.system_settings import SystemSettingsModel
from app.utils.time import now_timestamp

logger = logging.getLogger(__name__)

# Simple TTL cache for threshold to avoid DynamoDB call on every request
_cached_threshold: Optional[float] = None
_threshold_cache_time: Optional[float] = None
_CACHE_TTL_SECONDS = 60


class SystemSettingsRepository:
    """Repository for managing system-wide settings."""

    async def get_threshold(self) -> float:
        """Get quality score threshold (cached with 60s TTL)."""
        global _cached_threshold, _threshold_cache_time

        # Check cache
        if _cached_threshold is not None and _threshold_cache_time is not None:
            if time.time() - _threshold_cache_time < _CACHE_TTL_SECONDS:
                return _cached_threshold

        # Fetch from DynamoDB
        try:
            def _get():
                return SystemSettingsModel.get("quality_threshold")

            item = await asyncio.to_thread(_get)
            threshold = item.value_number or 8.0
        except DoesNotExist:
            threshold = 8.0
        except Exception as e:
            logger.warning(f"Error fetching threshold, using default: {str(e)}")
            threshold = 8.0

        # Update cache
        _cached_threshold = threshold
        _threshold_cache_time = time.time()
        return threshold

    async def set_threshold(self, value: float) -> float:
        """Set quality score threshold and update cache."""
        global _cached_threshold, _threshold_cache_time

        # Clamp value
        value = max(0.0, min(10.0, value))

        # Save to DynamoDB
        try:
            def _save():
                item = SystemSettingsModel("quality_threshold")
                item.value_number = value
                item.updated_at = now_timestamp()
                item.save()

            await asyncio.to_thread(_save)
        except Exception as e:
            logger.error(f"Error saving threshold: {str(e)}")
            raise

        # Update cache
        _cached_threshold = value
        _threshold_cache_time = time.time()
        return value
