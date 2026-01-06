"""Task Management Service.

Manages background tasks for asynchronous operations like app building.

Internal organization:
- task_operations.py: Task creation and retrieval
- retry_logic.py: Version conflict handling and retries
- progress_tracking.py: Status updates and progress messages
"""

import logging
from typing import Any, Dict, Optional

from application.entity.background_task import BackgroundTask
from common.service.entity_service import EntityService

from .task_operations import create_task, get_task
from .retry_logic import update_task_with_retry
from .progress_tracking import update_task_status, add_progress_update

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing background tasks."""

    def __init__(self, entity_service: EntityService):
        """Initialize task service."""
        self.entity_service = entity_service

    async def create_task(self, *args, **kwargs) -> BackgroundTask:
        """Create a new background task."""
        return await create_task(self.entity_service, *args, **kwargs)

    async def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get a task by technical ID."""
        return await get_task(self.entity_service, task_id)

    async def update_task(self, task: BackgroundTask, max_retries: int = 5) -> BackgroundTask:
        """Update a task entity in Cyoda with retry logic."""
        return await update_task_with_retry(self.entity_service, task, max_retries)

    async def update_task_status(self, *args, **kwargs) -> BackgroundTask:
        """Update task status and add progress message."""
        return await update_task_status(self.entity_service, *args, **kwargs)

    async def add_progress_update(self, *args, **kwargs) -> BackgroundTask:
        """Add a progress update to a task."""
        return await add_progress_update(self.entity_service, *args, **kwargs)


__all__ = ["TaskService"]
