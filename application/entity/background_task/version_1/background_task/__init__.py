"""BackgroundTask entity - Re-exports for backward compatibility."""

from .formatters import to_api_response
from .statistics import (
    calculate_statistics,
    format_duration,
    get_status_message,
)
from .task_model import (
    BackgroundTask,
    add_progress_message,
    update_status,
)

# Monkey-patch methods onto BackgroundTask class for backward compatibility
BackgroundTask.add_progress_message = (
    lambda self, message, progress=None, metadata=None: add_progress_message(
        self, message, progress, metadata
    )
)
BackgroundTask.update_status = (
    lambda self, status, message=None, progress=None, error=None: update_status(
        self, status, message, progress, error
    )
)
BackgroundTask._calculate_statistics = lambda self: calculate_statistics(
    self.status, self.progress, self.error, self.started_at, self.completed_at
)
BackgroundTask._get_status_message = lambda self: get_status_message(
    self.status, self.progress, self.error
)
BackgroundTask._format_duration = lambda self, seconds: format_duration(seconds)
BackgroundTask.to_api_response = lambda self: to_api_response(self)

__all__ = [
    "BackgroundTask",
    "add_progress_message",
    "update_status",
    "format_duration",
    "get_status_message",
    "calculate_statistics",
    "to_api_response",
]
