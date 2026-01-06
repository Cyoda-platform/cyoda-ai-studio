"""Helper functions for CLI process monitoring.

This module breaks down the monolithic monitor_cli_process function into
smaller, focused helpers following the Single Responsibility Principle.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Tuple

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import (
    COMMIT_TIMEOUT,
    DIFF_CATEGORY_ADDED,
    DIFF_CATEGORY_MODIFIED,
    DIFF_CATEGORY_UNTRACKED,
    MAX_CHANGED_FILES_IN_METADATA,
    PROGRESS_COMPLETE,
)

logger = logging.getLogger(__name__)


def extract_auth_info(
    tool_context: Optional[ToolContext],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract authentication information from tool context.

    Args:
        tool_context: Tool context containing auth information

    Returns:
        Tuple of (repo_url, installation_id, repository_type)
    """
    if not tool_context:
        return None, None, None

    repository_type = tool_context.state.get("repository_type")
    repo_url = tool_context.state.get("user_repository_url") or tool_context.state.get("repository_url")
    installation_id = tool_context.state.get("installation_id")

    logger.info(f"🔐 Extracted auth info - type: {repository_type}, url: {repo_url}, inst_id: {installation_id}")

    return repo_url, installation_id, repository_type


async def send_commit(
    repository_path: str,
    branch_name: str,
    tool_context: Optional[ToolContext],
    auth_repo_url: Optional[str],
    auth_installation_id: Optional[str],
    auth_repository_type: Optional[str],
    commit_type: str = "progress",
) -> Dict[str, Any]:
    """Send a git commit and push.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Tool context
        auth_repo_url: Repository URL for auth
        auth_installation_id: GitHub App installation ID
        auth_repository_type: Repository type (public/private)
        commit_type: Type of commit (initial/progress/final)

    Returns:
        Dict with commit result
    """
    from application.agents.github.tool_definitions.git import _commit_and_push_changes

    logger.info(f"🔍 [{branch_name}] Sending {commit_type} commit...")

    try:
        result = await asyncio.wait_for(
            _commit_and_push_changes(
                repository_path=repository_path,
                branch_name=branch_name,
                tool_context=tool_context,
                repo_url=auth_repo_url,
                installation_id=auth_installation_id,
                repository_type=auth_repository_type,
            ),
            timeout=COMMIT_TIMEOUT
        )
        logger.info(f"✅ [{branch_name}] {commit_type.capitalize()} commit completed")
        return result
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ [{branch_name}] {commit_type.capitalize()} commit timed out after {COMMIT_TIMEOUT}s")
        return {"status": "timeout"}
    except Exception as e:
        logger.error(f"❌ [{branch_name}] Failed to send {commit_type} commit: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def get_diff_summary(tool_context: Optional[ToolContext]) -> Tuple[list, dict]:
    """Get repository diff summary.

    Args:
        tool_context: Tool context

    Returns:
        Tuple of (changed_files list, diff_summary dict)
    """
    from application.agents.github.tool_definitions.repository import get_repository_diff

    changed_files = []
    diff_summary = {}

    if not tool_context:
        return changed_files, diff_summary

    try:
        diff_result = await get_repository_diff(tool_context)
        diff_data = json.loads(diff_result)

        for category in [DIFF_CATEGORY_MODIFIED, DIFF_CATEGORY_ADDED, DIFF_CATEGORY_UNTRACKED]:
            changed_files.extend(diff_data.get(category, []))

        diff_summary = {
            DIFF_CATEGORY_ADDED: diff_data.get(DIFF_CATEGORY_ADDED, []),
            DIFF_CATEGORY_MODIFIED: diff_data.get(DIFF_CATEGORY_MODIFIED, []),
            "deleted": diff_data.get("deleted", []),
            DIFF_CATEGORY_UNTRACKED: diff_data.get(DIFF_CATEGORY_UNTRACKED, [])
        }
    except Exception as e:
        logger.warning(f"Could not get diff: {e}")

    return changed_files, diff_summary


async def update_task_completed(
    task_id: str,
    changed_files: list,
    diff_summary: dict,
) -> None:
    """Update BackgroundTask to completed status.

    Args:
        task_id: Task ID
        changed_files: List of changed file paths
        diff_summary: Dict with categorized changes
    """
    from services.services import get_task_service

    try:
        task_service = get_task_service()

        files_summary = f"{len(changed_files)} files changed" if changed_files else "No files changed"

        current_task = await task_service.get_task(task_id)
        existing_metadata = current_task.metadata if current_task else {}

        updated_metadata = {
            **existing_metadata,
            "changed_files": changed_files[:MAX_CHANGED_FILES_IN_METADATA],
            "diff": diff_summary
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


async def update_task_progress(
    task_id: str,
    progress: int,
    elapsed_time: int,
    pid: int,
) -> None:
    """Update BackgroundTask with progress.

    Args:
        task_id: Task ID
        progress: Progress percentage
        elapsed_time: Elapsed time in seconds
        pid: Process ID
    """
    from services.services import get_task_service

    try:
        task_service = get_task_service()
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


async def update_task_with_diff(
    task_id: str,
    commit_result: dict,
) -> None:
    """Update BackgroundTask with latest diff info from commit.

    Args:
        task_id: Task ID
        commit_result: Result dict from commit operation
    """
    from services.services import get_task_service

    if commit_result.get("status") != "success":
        return

    try:
        task_service = get_task_service()
        current_task = await task_service.get_task(task_id)
        existing_metadata = current_task.metadata if current_task else {}

        updated_metadata = {
            **existing_metadata,
            "changed_files": commit_result.get("changed_files", [])[:MAX_CHANGED_FILES_IN_METADATA],
            "diff": commit_result.get("diff", {})
        }

        await task_service.add_progress_update(
            task_id=task_id,
            message="Progress committed",
            metadata=updated_metadata,
        )
        logger.info(f"📊 Updated BackgroundTask {task_id} with latest diff info")
    except Exception as e:
        logger.warning(f"⚠️ Failed to update task with diff info: {e}")


async def update_task_failed(
    task_id: str,
    error_message: str,
) -> None:
    """Update BackgroundTask to failed status.

    Args:
        task_id: Task ID
        error_message: Error message
    """
    from services.services import get_task_service

    try:
        task_service = get_task_service()
        await task_service.update_task_status(
            task_id=task_id,
            status="failed",
            message=error_message,
            progress=0,
            error=error_message,
        )
        logger.info(f"❌ Updated BackgroundTask {task_id} to failed")
    except Exception as e:
        logger.warning(f"⚠️ Failed to update BackgroundTask on failure: {e}")


async def unregister_process(pid: int) -> None:
    """Unregister process from process manager.

    Args:
        pid: Process ID
    """
    try:
        from application.agents.shared.process_manager import get_process_manager
        process_manager = get_process_manager()
        await process_manager.unregister_process(pid)
        logger.info(f"✅ Unregistered CLI process {pid}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to unregister process: {e}")
