"""
Task Management Service

Manages background tasks for asynchronous operations like app building.
"""

import logging
from typing import Any, Dict, Optional

from application.entity.background_task import BackgroundTask
from common.service.entity_service import EntityService

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing background tasks."""

    def __init__(self, entity_service: EntityService):
        """
        Initialize task service.

        Args:
            entity_service: Entity service for Cyoda operations
        """
        self.entity_service = entity_service

    async def create_task(
        self,
        user_id: str,
        task_type: str,
        name: str,
        description: str = "",
        branch_name: Optional[str] = None,
        language: Optional[str] = None,
        user_request: Optional[str] = None,
        conversation_id: Optional[str] = None,
        repository_path: Optional[str] = None,
        repository_type: Optional[str] = None,
        build_id: Optional[str] = None,
        namespace: Optional[str] = None,
        env_url: Optional[str] = None,
        **kwargs: Any,
    ) -> BackgroundTask:
        """
        Create a new background task.

        Args:
            user_id: User ID who owns the task
            task_type: Type of task (e.g., 'build_app', 'environment_deployment')
            name: Task name
            description: Task description
            branch_name: Git branch name (for build tasks)
            language: Programming language (for build tasks)
            user_request: Original user request
            conversation_id: Associated conversation ID
            repository_path: Repository path (for build tasks)
            repository_type: Repository type (public/private)
            build_id: Cloud manager build ID (for deployment tasks)
            namespace: Deployment namespace (for deployment tasks)
            env_url: Environment URL (for deployment tasks)
            **kwargs: Additional task-specific parameters

        Returns:
            Created BackgroundTask entity
        """
        task = BackgroundTask(
            user_id=user_id,
            task_type=task_type,
            name=name,
            description=description,
            status="pending",
            progress=0,
            branch_name=branch_name,
            language=language,
            user_request=user_request,
            conversation_id=conversation_id,
            repository_path=repository_path,
            repository_type=repository_type,
            build_id=build_id,
            namespace=namespace,
            env_url=env_url,
        )

        # Add any additional kwargs to workflow_cache
        if kwargs:
            task.workflow_cache.update(kwargs)

        # Save to Cyoda
        entity_data = task.model_dump(by_alias=False)
        response = await self.entity_service.save(
            entity=entity_data,
            entity_class=BackgroundTask.ENTITY_NAME,
            entity_version=str(BackgroundTask.ENTITY_VERSION),
        )

        # Return the created task
        saved_data = response.data if hasattr(response, "data") else response
        created_task = BackgroundTask(**saved_data)

        logger.info(
            f"✅ Created background task {created_task.technical_id} "
            f"(type={task_type}, user={user_id})"
        )

        return created_task

    async def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """
        Get a task by technical ID.

        Args:
            task_id: Task technical ID

        Returns:
            BackgroundTask entity or None if not found
        """
        try:
            response = await self.entity_service.get_by_id(
                entity_id=task_id,
                entity_class=BackgroundTask.ENTITY_NAME,
                entity_version=str(BackgroundTask.ENTITY_VERSION),
            )

            if response and hasattr(response, "data"):
                return BackgroundTask(**response.data)
            elif response:
                return BackgroundTask(**response)
            return None
        except Exception as e:
            from common.exception import is_not_found

            if is_not_found(e):
                return None
            raise

    async def update_task(
        self,
        task: BackgroundTask,
        max_retries: int = 5,
    ) -> BackgroundTask:
        """
        Update a task entity in Cyoda.
        Includes retry logic for version conflict errors.

        Args:
            task: BackgroundTask entity to update
            max_retries: Maximum number of retry attempts

        Returns:
            Updated BackgroundTask entity
        """
        import asyncio
        import copy

        base_delay = 0.1  # 100ms base delay

        for attempt in range(max_retries):
            try:
                # If this is a retry, fetch the latest version
                if attempt > 0:
                    logger.debug(
                        f"Retry {attempt + 1}/{max_retries}: Fetching latest task version"
                    )
                    fresh_task = await self.get_task(task.technical_id)
                    if not fresh_task:
                        raise ValueError(f"Task {task.technical_id} not found")

                    # Re-apply changes from the input task to the fresh version
                    # Copy over the fields that should be updated
                    fresh_task.status = task.status
                    fresh_task.progress = task.progress
                    fresh_task.progress_messages = copy.deepcopy(task.progress_messages)
                    fresh_task.started_at = task.started_at
                    fresh_task.completed_at = task.completed_at
                    fresh_task.result = task.result
                    fresh_task.error = task.error
                    fresh_task.error_code = task.error_code
                    fresh_task.process_pid = task.process_pid
                    fresh_task.build_job_id = task.build_job_id

                    task = fresh_task

                entity_data = task.model_dump(by_alias=False)

                response = await self.entity_service.update(
                    entity_id=task.technical_id,
                    entity=entity_data,
                    entity_class=BackgroundTask.ENTITY_NAME,
                    entity_version=str(BackgroundTask.ENTITY_VERSION),
                )

                saved_data = response.data if hasattr(response, "data") else response
                return BackgroundTask(**saved_data)

            except Exception as e:
                error_str = str(e).lower()
                # Check for version conflict errors
                is_version_conflict = (
                    "422" in error_str
                    or "500" in error_str
                    or "version mismatch" in error_str
                    or "earliestupdateaccept" in error_str
                    or "was changed by another transaction" in error_str
                )

                if is_version_conflict and attempt < max_retries - 1:
                    # Exponential backoff
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Version conflict updating task {task.technical_id} "
                        f"(attempt {attempt + 1}/{max_retries}). Retrying in {delay:.3f}s..."
                    )
                    await asyncio.sleep(delay)
                    continue  # Retry
                else:
                    # Non-retryable error or max retries reached
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Failed to update task after {max_retries} attempts: {e}"
                        )
                    raise

        raise RuntimeError("Update task failed after all retries")

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        message: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        **kwargs: Any,
    ) -> BackgroundTask:
        """
        Update task status and add progress message.

        Args:
            task_id: Task technical ID
            status: New status (pending, running, completed, failed)
            message: Optional progress message
            progress: Optional progress percentage (0-100)
            error: Optional error message
            **kwargs: Additional fields to update

        Returns:
            Updated BackgroundTask entity
        """
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update status
        task.update_status(status, message, progress, error)

        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Save to Cyoda
        return await self.update_task(task)

    async def add_progress_update(
        self,
        task_id: str,
        message: str,
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackgroundTask:
        """
        Add a progress update to a task.

        Args:
            task_id: Task technical ID
            message: Progress message
            progress: Optional progress percentage
            metadata: Optional metadata

        Returns:
            Updated BackgroundTask entity
        """
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.add_progress_message(message, progress, metadata)

        return await self.update_task(task)

