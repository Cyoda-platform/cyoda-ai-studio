"""Task update operations for CLI process monitoring."""

from __future__ import annotations

import logging
from typing import Optional

from application.agents.github.tool_definitions.common.constants import (
    CLI_PROCESS_TIMEOUT,
    DIFF_CATEGORY_ADDED,
    DIFF_CATEGORY_DELETED,
    DIFF_CATEGORY_MODIFIED,
    DIFF_CATEGORY_UNTRACKED,
    MAX_CHANGED_FILES_IN_METADATA,
    PROGRESS_COMPLETE,
    PROGRESS_MAX_BEFORE_COMPLETION,
)

logger = logging.getLogger(__name__)


async def _update_task_on_completion(
    task_id: str, changed_files: list, diff_summary: dict
) -> None:
    """Update background task to completed status.

    Args:
        task_id: Background task ID
        changed_files: List of changed file paths
        diff_summary: Dictionary with diff categories
    """
    # Local import for test mocking compatibility
    from services.services import get_task_service

    try:
        task_service = get_task_service()
        files_summary = (
            f"{len(changed_files)} files changed"
            if changed_files
            else "No files changed"
        )

        current_task = await task_service.get_task(task_id)
        existing_metadata = current_task.metadata if current_task else {}

        updated_metadata = {
            **existing_metadata,
            "changed_files": changed_files[:MAX_CHANGED_FILES_IN_METADATA],
            "diff": diff_summary,
        }

        await task_service.update_task_status(
            task_id=task_id,
            status="completed",
            message=f"Process completed - {files_summary}",
            progress=PROGRESS_COMPLETE,
            metadata=updated_metadata,
        )
        logger.info(f"✅ Updated BackgroundTask {task_id} to completed")
    except Exception as e:
        logger.warning(f"⚠️ Failed to update BackgroundTask: {e}")


async def _update_task_progress(task_id: str, elapsed_time: float, pid: int) -> None:
    """Update background task with current progress.

    Args:
        task_id: Background task ID
        elapsed_time: Time elapsed since start
        pid: Process ID
    """
    # Local import for test mocking compatibility
    from services.services import get_task_service

    try:
        task_service = get_task_service()
        progress = min(
            PROGRESS_MAX_BEFORE_COMPLETION,
            int((elapsed_time / CLI_PROCESS_TIMEOUT) * 100),
        )

        await task_service.update_task_status(
            task_id=task_id,
            status="running",
            message=f"Process in progress... ({int(elapsed_time)}s elapsed)",
            progress=progress,
            metadata={"elapsed_time": int(elapsed_time), "pid": pid},
        )
        logger.info(f"📊 Updated BackgroundTask {task_id} progress: {progress}%")
    except Exception as e:
        logger.warning(f"⚠️ Failed to update BackgroundTask progress: {e}")


async def _update_task_with_commit_info(
    task_id: str, commit_result: dict
) -> None:
    """Update task with latest commit information.

    Args:
        task_id: Background task ID
        commit_result: Result from commit operation
    """
    if commit_result.get("status") != "success":
        return

    # Local import for test mocking compatibility
    from services.services import get_task_service

    try:
        task_service = get_task_service()
        current_task = await task_service.get_task(task_id)
        existing_metadata = current_task.metadata if current_task else {}

        updated_metadata = {
            **existing_metadata,
            "changed_files": commit_result.get("changed_files", [])[
                :MAX_CHANGED_FILES_IN_METADATA
            ],
            "diff": commit_result.get("diff", {}),
        }

        await task_service.add_progress_update(
            task_id=task_id,
            message="Progress committed",
            metadata=updated_metadata,
        )
        logger.info(f"📊 Updated BackgroundTask {task_id} with latest diff info")
    except Exception as e:
        logger.warning(f"⚠️ Failed to update task with diff info: {e}")


async def _handle_process_timeout_task_update(task_id: str, timeout_seconds: int) -> None:
    """Update task to failed status on timeout.

    Args:
        task_id: Background task ID
        timeout_seconds: Timeout threshold in seconds
    """
    # Local import for test mocking compatibility
    from services.services import get_task_service

    try:
        task_service = get_task_service()
        await task_service.update_task_status(
            task_id=task_id,
            status="failed",
            message=f"Process timeout after {timeout_seconds} seconds",
            progress=0,
            error=f"Process exceeded {timeout_seconds} seconds timeout",
        )
        logger.info(f"❌ Updated BackgroundTask {task_id} to failed (timeout)")
    except Exception as e:
        logger.warning(f"⚠️ Failed to update BackgroundTask on timeout: {e}")
