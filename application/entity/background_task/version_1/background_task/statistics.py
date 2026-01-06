"""Statistics calculation for BackgroundTask."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2h 30m", "45s")
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def get_status_message(status: str, progress: int, error: str) -> str:
    """Get human-readable status message (statistic #3).

    Args:
        status: Task status
        progress: Progress percentage
        error: Error message (if any)

    Returns:
        Formatted status message
    """
    status_messages = {
        "pending": "Waiting to start",
        "running": f"In progress - {progress}% complete",
        "completed": "Completed successfully",
        "failed": f"Failed: {error or 'Unknown error'}",
        "cancelled": "Cancelled",
    }
    return status_messages.get(status, f"Status: {status}")


def calculate_statistics(
    status: str,
    progress: int,
    error: str,
    started_at: str,
    completed_at: str,
) -> Dict[str, Any]:
    """Calculate top 3 task statistics for UI display.

    Args:
        status: Task status
        progress: Progress percentage
        error: Error message (if any)
        started_at: ISO timestamp when task started
        completed_at: ISO timestamp when task completed

    Returns:
        Dictionary with 3 key statistics
    """
    now = datetime.now(timezone.utc)
    stats: Dict[str, Any] = {
        "duration_formatted": "0s",
        "time_remaining_formatted": None,
        "status_message": get_status_message(status, progress, error),
    }

    # 1. Duration - how long the task has been running
    if started_at:
        try:
            started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end_time = (
                datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                if completed_at
                else now
            )
            duration = (end_time - started).total_seconds()
            stats["duration_formatted"] = format_duration(duration)

            # 2. Time remaining - estimated time until completion
            if status == "running" and progress > 0 and duration > 0:
                progress_rate = (progress / duration) * 60  # % per minute
                if progress_rate > 0:
                    remaining_progress = 100 - progress
                    time_remaining = (remaining_progress / progress_rate) * 60
                    stats["time_remaining_formatted"] = format_duration(time_remaining)

        except (ValueError, AttributeError):
            pass

    return stats
