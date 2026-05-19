"""Time and timestamp utilities."""

import time
from datetime import datetime


def now_timestamp() -> int:
    """Get current Unix timestamp as integer."""
    return int(time.time())


def timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert Unix timestamp to datetime object."""
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime object to Unix timestamp."""
    return int(dt.timestamp())
