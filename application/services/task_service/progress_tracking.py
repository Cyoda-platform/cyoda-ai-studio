"""Progress tracking and status updates for tasks."""

import logging
from typing import Any, Dict, Optional

from application.entity.background_task import BackgroundTask
from common.service.entity_service import EntityService

logger = logging.getLogger(__name__)


async def update_task_status(
    entity_service: EntityService,
    task_id: str,
    status: str,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    error: Optional[str] = None,
    **kwargs: Any,
) -> BackgroundTask:
    """Update task status and add progress message."""
    from .retry_logic import update_task_with_retry
    from .task_operations import get_task

    task = await get_task(entity_service, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    # Update status
    task.update_status(status, message, progress, error)

    # Update any additional fields
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)

    # Save to Cyoda
    return await update_task_with_retry(entity_service, task)


async def add_progress_update(
    entity_service: EntityService,
    task_id: str,
    message: str,
    progress: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> BackgroundTask:
    """Add a progress update to a task."""
    from .retry_logic import update_task_with_retry
    from .task_operations import get_task

    task = await get_task(entity_service, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    task.add_progress_message(message, progress, metadata)

    return await update_task_with_retry(entity_service, task)


__all__ = [
    "update_task_status",
    "add_progress_update",
]
