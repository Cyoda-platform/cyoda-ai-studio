"""Retry logic for task updates with version conflict handling."""

import asyncio
import logging
from typing import Optional

from application.entity.background_task import BackgroundTask
from common.service.entity_service import EntityService

logger = logging.getLogger(__name__)


async def _fetch_fresh_task_version(
    entity_service: EntityService, task_id: str, max_retries: int, attempt: int
) -> BackgroundTask:
    """Fetch latest task version on retry."""
    from .task_operations import get_task

    logger.debug(f"Retry {attempt + 1}/{max_retries}: Fetching latest task version")
    fresh_task = await get_task(entity_service, task_id)
    if not fresh_task:
        raise ValueError(f"Task {task_id} not found")
    return fresh_task


def _reapply_task_updates(
    fresh_task: BackgroundTask, original_task: BackgroundTask
) -> BackgroundTask:
    """Reapply updates from original task to fresh version."""
    import copy

    fresh_task.status = original_task.status
    fresh_task.progress = original_task.progress
    fresh_task.progress_messages = copy.deepcopy(original_task.progress_messages)
    fresh_task.started_at = original_task.started_at
    fresh_task.completed_at = original_task.completed_at
    fresh_task.result = original_task.result
    fresh_task.error = original_task.error
    fresh_task.error_code = original_task.error_code
    fresh_task.process_pid = original_task.process_pid
    fresh_task.build_job_id = original_task.build_job_id

    return fresh_task


async def _persist_task(
    entity_service: EntityService, task: BackgroundTask
) -> BackgroundTask:
    """Persist task to Cyoda."""
    entity_data = task.model_dump(by_alias=False)
    response = await entity_service.update(
        entity_id=task.technical_id,
        entity=entity_data,
        entity_class=BackgroundTask.ENTITY_NAME,
        entity_version=str(BackgroundTask.ENTITY_VERSION),
    )
    saved_data = response.data if hasattr(response, "data") else response
    return BackgroundTask(**saved_data)


def _is_version_conflict(error: Exception) -> bool:
    """Check if error is version conflict."""
    error_str = str(error).lower()
    return (
        "422" in error_str
        or "500" in error_str
        or "version mismatch" in error_str
        or "earliestupdateaccept" in error_str
        or "was changed by another transaction" in error_str
    )


async def update_task_with_retry(
    entity_service: EntityService,
    task: BackgroundTask,
    max_retries: int = 5,
) -> BackgroundTask:
    """Update a task entity in Cyoda with retry logic.

    Fetches latest version on conflict and reapplies updates.
    Uses exponential backoff for retry delays.
    """
    base_delay = 0.1

    for attempt in range(max_retries):
        try:
            # Fetch fresh version on retry
            if attempt > 0:
                fresh_task = await _fetch_fresh_task_version(
                    entity_service, task.technical_id, max_retries, attempt
                )
                task = _reapply_task_updates(fresh_task, task)

            # Persist task
            return await _persist_task(entity_service, task)

        except Exception as e:
            # Check if retryable error
            if _is_version_conflict(e) and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Version conflict updating task {task.technical_id} "
                    f"(attempt {attempt + 1}/{max_retries}). Retrying in {delay:.3f}s..."
                )
                await asyncio.sleep(delay)
                continue
            else:
                # Non-retryable or final attempt
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to update task after {max_retries} attempts: {e}"
                    )
                raise

    raise RuntimeError("Update task failed after all retries")


__all__ = [
    "_fetch_fresh_task_version",
    "_reapply_task_updates",
    "_persist_task",
    "_is_version_conflict",
    "update_task_with_retry",
]
