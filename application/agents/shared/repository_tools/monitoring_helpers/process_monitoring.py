"""Build process monitoring with periodic commits.

This module handles monitoring build processes with timeout and periodic commits.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.constants import (
    DEFAULT_BUILD_TIMEOUT_SECONDS,
    PROCESS_CHECK_INTERVAL_SECONDS,
    PROCESS_COMMIT_INTERVAL_SECONDS,
    PROCESS_KILL_GRACE_SECONDS,
)
from services.services import get_task_service

from .output_streaming import _stream_process_output

logger = logging.getLogger(__name__)


def _extract_auth_info(
    tool_context: Optional[ToolContext],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract authentication info from tool context.

    Args:
        tool_context: Tool context

    Returns:
        Tuple of (repo_url, installation_id, repository_type)
    """
    if not tool_context:
        return None, None, None

    repo_type = tool_context.state.get("repository_type")
    repo_url = tool_context.state.get("user_repository_url") or tool_context.state.get(
        "repository_url"
    )
    inst_id = tool_context.state.get("installation_id")

    logger.info(
        f"🔐 Extracted auth info - type: {repo_type}, url: {repo_url}, inst_id: {inst_id}"
    )
    return repo_url, inst_id, repo_type


async def _send_initial_commit(
    repository_path: str,
    branch_name: str,
    tool_context: Optional[ToolContext],
    auth_repo_url: Optional[str],
    auth_installation_id: Optional[str],
    auth_repository_type: Optional[str],
) -> None:
    """Send initial commit when process starts.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Tool context
        auth_repo_url: Repository URL
        auth_installation_id: Installation ID
        auth_repository_type: Repository type
    """
    if not tool_context:
        return

    try:
        logger.info(f"🔍 [{branch_name}] Sending initial commit...")
        from application.agents.github.tools import _commit_and_push_changes

        await _commit_and_push_changes(
            repository_path=repository_path,
            branch_name=branch_name,
            tool_context=tool_context,
            repo_url=auth_repo_url,
            installation_id=auth_installation_id,
            repository_type=auth_repository_type,
        )
        logger.info(f"✅ [{branch_name}] Initial commit completed")
    except Exception as e:
        logger.error(
            f"❌ [{branch_name}] Failed to send initial commit: {e}", exc_info=True
        )


async def _handle_process_completion(
    process: any,
    pid: int,
    task_id: Optional[str],
    elapsed_time: int,
) -> None:
    """Handle process completion.

    Args:
        process: The subprocess
        pid: Process ID
        task_id: Background task ID
        elapsed_time: Elapsed time in seconds
    """
    logger.info(f"✅ Process {pid} completed normally")

    final_status = "completed" if process.returncode == 0 else "failed"
    final_message = (
        "Build completed successfully - ready for setup"
        if process.returncode == 0
        else f"Build process exited with non-zero code: {process.returncode}"
    )

    from application.agents.shared.process_manager import get_process_manager

    process_manager = get_process_manager()
    await process_manager.unregister_process(pid)

    if task_id:
        try:
            task_service = get_task_service()
            await task_service.update_task_status(
                task_id=task_id,
                status=final_status,
                message=final_message,
                progress=100 if final_status == "completed" else 0,
                metadata={"elapsed_time": elapsed_time, "pid": pid},
            )
            logger.info(f"✅ Updated BackgroundTask {task_id} to {final_status}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update BackgroundTask: {e}")


async def _handle_periodic_commit(
    elapsed_time: int,
    task_id: Optional[str],
    repository_path: str,
    branch_name: str,
    tool_context: Optional[ToolContext],
    auth_repo_url: Optional[str],
    auth_installation_id: Optional[str],
    auth_repository_type: Optional[str],
) -> None:
    """Handle periodic commit during build.

    Args:
        elapsed_time: Elapsed time in seconds
        task_id: Background task ID
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Tool context
        auth_repo_url: Repository URL
        auth_installation_id: Installation ID
        auth_repository_type: Repository type
    """
    if not tool_context or elapsed_time % PROCESS_COMMIT_INTERVAL_SECONDS != 0:
        return

    try:
        logger.info(f"📊 [{branch_name}] Committing progress...")
        from application.agents.github.tools import _commit_and_push_changes

        commit_result = await _commit_and_push_changes(
            repository_path=repository_path,
            branch_name=branch_name,
            tool_context=tool_context,
            repo_url=auth_repo_url,
            installation_id=auth_installation_id,
            repository_type=auth_repository_type,
        )

        if task_id and commit_result.get("status") == "success":
            await _update_task_with_commit_info(task_id, commit_result)

        logger.info(f"✅ [{branch_name}] Progress commit completed")
    except Exception as e:
        logger.warning(f"⚠️ [{branch_name}] Failed to commit/push: {e}")


async def _update_task_with_commit_info(task_id: str, commit_result: dict) -> None:
    """Update task with commit information.

    Args:
        task_id: Background task ID
        commit_result: Result from commit operation
    """
    try:
        task_service = get_task_service()
        current_task = await task_service.get_task(task_id)
        existing_metadata = current_task.metadata if current_task else {}

        updated_metadata = {
            **existing_metadata,
            "changed_files": commit_result.get("changed_files", [])[:20],
            "diff": commit_result.get("diff", {}),
        }

        await task_service.add_progress_update(
            task_id=task_id,
            message="Progress committed",
            metadata=updated_metadata,
        )
        logger.info(f"📊 Updated BackgroundTask {task_id} with diff info")
    except Exception as e:
        logger.warning(f"⚠️ Failed to update task with diff info: {e}")


async def _handle_timeout_exceeded(
    pid: int,
    task_id: Optional[str],
    timeout_seconds: int,
    process: any,
) -> None:
    """Handle timeout exceeded.

    Args:
        pid: Process ID
        task_id: Background task ID
        timeout_seconds: Timeout in seconds
        process: The subprocess
    """
    logger.error(
        f"⏰ Process exceeded {timeout_seconds} seconds, terminating... (PID: {pid})"
    )

    from application.agents.shared.process_manager import get_process_manager

    process_manager = get_process_manager()
    await process_manager.unregister_process(pid)

    if task_id:
        try:
            task_service = get_task_service()
            await task_service.update_task_status(
                task_id=task_id,
                status="failed",
                message=f"Build timeout after {timeout_seconds} seconds",
                progress=0,
                error=f"Process exceeded {timeout_seconds} seconds timeout",
            )
            logger.info(f"❌ Updated BackgroundTask {task_id} to failed (timeout)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update BackgroundTask on timeout: {e}")

    await _terminate_process(process)


async def _monitor_build_process(
    process: any,
    repository_path: str,
    branch_name: str,
    timeout_seconds: int = DEFAULT_BUILD_TIMEOUT_SECONDS,
    tool_context: Optional[ToolContext] = None,
) -> None:
    """Monitor build process with periodic checks and git commits.

    Args:
        process: The asyncio subprocess
        repository_path: Path to repository
        branch_name: Branch name
        timeout_seconds: Maximum time to wait before terminating
        tool_context: Tool context for conversation and task updates
    """
    pid = process.pid
    task_id = tool_context.state.get("background_task_id") if tool_context else None
    auth_repo_url, auth_installation_id, auth_repository_type = _extract_auth_info(
        tool_context
    )

    logger.info(
        f"🔍 [{branch_name}] Monitoring started for PID {pid}, task_id: {task_id}"
    )

    asyncio.create_task(_stream_process_output(process=process, task_id=task_id))
    await _send_initial_commit(
        repository_path,
        branch_name,
        tool_context,
        auth_repo_url,
        auth_installation_id,
        auth_repository_type,
    )

    check_interval = PROCESS_CHECK_INTERVAL_SECONDS
    elapsed_time = 0

    while elapsed_time < timeout_seconds:
        try:
            remaining_time = min(check_interval, timeout_seconds - elapsed_time)
            await asyncio.wait_for(process.wait(), timeout=remaining_time)
            await _handle_process_completion(process, pid, task_id, elapsed_time)
            return
        except asyncio.TimeoutError:
            elapsed_time += remaining_time
            await _handle_periodic_commit(
                elapsed_time,
                task_id,
                repository_path,
                branch_name,
                tool_context,
                auth_repo_url,
                auth_installation_id,
                auth_repository_type,
            )

    await _handle_timeout_exceeded(pid, task_id, timeout_seconds, process)


async def _terminate_process(process: any) -> None:
    """
    Terminate a process gracefully, then forcefully if needed.

    Args:
        process: The asyncio subprocess to terminate
    """
    kill_grace_seconds = PROCESS_KILL_GRACE_SECONDS
    try:
        process.terminate()
    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(process.wait(), timeout=kill_grace_seconds)
    except asyncio.TimeoutError:
        logger.error(f"⚠️ Process did not terminate, killing... (PID: {process.pid})")
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()
