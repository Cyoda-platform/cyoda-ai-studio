"""Task update operations for deployment monitoring."""

from __future__ import annotations

import logging
from typing import Optional

from services.services import get_task_service

logger = logging.getLogger(__name__)

# Message templates
FAILURE_MESSAGE_TEMPLATE = "Environment deployment failed: {status}"
FAILURE_ERROR_TEMPLATE = "Deployment status: {status} (state: {state})"
SUCCESS_MESSAGE_TEMPLATE = "Environment deployment completed: {status}"
PROGRESS_MESSAGE_TEMPLATE = "Deployment {state}: {status}"
PROGRESS_LOG_TEMPLATE = "Deployment {build_id} progress: {progress}% ({state})"
FAILURE_LOG_TEMPLATE = "Deployment {build_id} failed: {error}"
SUCCESS_LOG_TEMPLATE = "Deployment {build_id} completed successfully"


async def _update_task_failed(
    task_id: str,
    build_id: str,
    message: str,
    error: str,
    namespace: Optional[str],
    env_url: Optional[str],
    state: str,
) -> None:
    """Update task status to failed.

    Args:
        task_id: Task ID
        build_id: Build ID
        message: Failure message
        error: Error details
        namespace: Deployment namespace
        env_url: Environment URL
        state: Deployment state
    """
    task_service = get_task_service()
    await task_service.update_task_status(
        task_id=task_id,
        status="failed",
        message=message,
        progress=0,
        error=error,
        metadata={
            "build_id": build_id,
            "namespace": namespace,
            "env_url": env_url,
            "state": state,
        },
    )
    logger.error(f"Deployment {build_id} failed: {error}")


async def _update_task_completed(
    task_id: str,
    build_id: str,
    message: str,
    namespace: Optional[str],
    env_url: Optional[str],
) -> None:
    """Update task status to completed.

    Args:
        task_id: Task ID
        build_id: Build ID
        message: Success message
        namespace: Deployment namespace
        env_url: Environment URL
    """
    task_service = get_task_service()
    await task_service.update_task_status(
        task_id=task_id,
        status="completed",
        message=message,
        progress=100,
        metadata={
            "build_id": build_id,
            "namespace": namespace,
            "env_url": env_url,
        },
    )
    logger.info(f"Deployment {build_id} completed successfully")


async def _update_task_progress(
    task_id: str,
    build_id: str,
    state: str,
    status: str,
    progress: int,
    check_num: int,
    namespace: Optional[str],
    env_url: Optional[str],
) -> None:
    """Add progress update to task.

    Args:
        task_id: Task ID
        build_id: Build ID
        state: Deployment state
        status: Deployment status
        progress: Progress percentage
        check_num: Check number
        namespace: Deployment namespace
        env_url: Environment URL
    """
    task_service = get_task_service()
    await task_service.add_progress_update(
        task_id=task_id,
        message=f"Deployment {state}: {status}",
        progress=progress,
        metadata={
            "build_id": build_id,
            "namespace": namespace,
            "env_url": env_url,
            "state": state,
            "check_num": check_num + 1,
        },
    )
    logger.info(f"Deployment {build_id} progress: {progress}% ({state})")


async def _get_task_info(task_id: str) -> tuple[str | None, str | None]:
    """Get task environment URL and namespace.

    Args:
        task_id: BackgroundTask technical ID

    Returns:
        Tuple of (env_url, namespace)
    """
    task_service = get_task_service()
    task = await task_service.get_task(task_id)
    env_url = task.env_url if task else None
    namespace = task.namespace if task else None
    return env_url, namespace
