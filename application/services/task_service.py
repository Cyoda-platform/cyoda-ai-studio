"""Task Management Service.

Manages background tasks for asynchronous operations like app building.
"""

# Re-export from task_service package for backward compatibility
from .task_service import TaskService

__all__ = ["TaskService"]
