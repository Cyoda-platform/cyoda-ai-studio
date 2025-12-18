"""
Task Repository for background task data access operations.

Provides clean abstraction for task entity operations.
"""

import logging
from typing import Optional

from services.services import get_task_service

logger = logging.getLogger(__name__)


class TaskRepository:
    """
    Repository for background task entity operations.

    Wraps task service with repository pattern for consistency.
    """

    def __init__(self, task_service=None):
        """
        Initialize task repository.

        Args:
            task_service: Task service for data access (optional, uses singleton if not provided)
        """
        self.task_service = task_service or get_task_service()

    async def get_by_id(self, task_id: str):
        """
        Get task by ID.

        Args:
            task_id: Task technical ID

        Returns:
            BackgroundTask object or None if not found

        Example:
            >>> repo = TaskRepository()
            >>> task = await repo.get_by_id("task-123")
        """
        return await self.task_service.get_task(task_id)

    async def get_tasks_by_ids(self, task_ids: list):
        """
        Get multiple tasks by IDs.

        Args:
            task_ids: List of task technical IDs

        Returns:
            List of BackgroundTask objects (skips not found)

        Example:
            >>> repo = TaskRepository()
            >>> tasks = await repo.get_tasks_by_ids(["task-1", "task-2"])
        """
        tasks = []
        for task_id in task_ids:
            try:
                task = await self.task_service.get_task(task_id)
                if task:
                    tasks.append(task)
            except Exception as e:
                logger.warning(f"Failed to get task {task_id}: {e}")
        return tasks
