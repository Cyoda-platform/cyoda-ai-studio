"""
BackgroundTask Entity for AI Assistant Application

Represents an asynchronous task (like app building) stored in Cyoda.
Tracks task progress, status, and results.
"""

# Re-export all public APIs from the background_task package
from .background_task import (
    BackgroundTask,
    add_progress_message,
    update_status,
    format_duration,
    get_status_message,
    calculate_statistics,
    to_api_response,
)

__all__ = [
    "BackgroundTask",
    "add_progress_message",
    "update_status",
    "format_duration",
    "get_status_message",
    "calculate_statistics",
    "to_api_response",
]
