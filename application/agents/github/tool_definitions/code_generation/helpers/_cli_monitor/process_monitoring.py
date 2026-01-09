"""Process monitoring and completion handling for CLI processes."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import (
    CLI_PROCESS_TIMEOUT,
    COMMIT_INTERVAL_DEFAULT,
    PROCESS_CHECK_INTERVAL,
    PROGRESS_UPDATE_INTERVAL,
)
from application.agents.shared.process_manager import get_process_manager
from application.agents.shared.process_utils import _is_process_running
from application.agents.shared.repository_tools import _terminate_process

from .._temp_file_cleanup import log_temp_file_preserved
from .commit_operations import (
    AuthInfo,
    _commit_progress,
    _extract_auth_info,
    _get_diff_summary,
    _send_final_commit,
    _send_initial_commit,
)
from .task_updates import (
    _handle_process_timeout_task_update,
    _update_task_on_completion,
    _update_task_progress,
    _update_task_with_commit_info,
)

logger = logging.getLogger(__name__)


@dataclass
class MonitorConfig:
    """Configuration for CLI process monitoring."""

    process: Any
    repository_path: str
    branch_name: str
    timeout_seconds: int = CLI_PROCESS_TIMEOUT
    tool_context: Optional[ToolContext] = None
    prompt_file: Optional[str] = None
    output_file: Optional[str] = None
    commit_interval: int = COMMIT_INTERVAL_DEFAULT
    progress_update_interval: int = PROGRESS_UPDATE_INTERVAL


async def _unregister_process(pid: int) -> None:
    """Unregister process from process manager.

    Args:
        pid: Process ID to unregister
    """
    try:
        process_manager = get_process_manager()
        await process_manager.unregister_process(pid)
        logger.info(f"✅ Unregistered CLI process {pid}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to unregister process: {e}")


async def _handle_normal_completion(config: MonitorConfig, auth_info: AuthInfo) -> None:
    """Handle normal process completion.

    Args:
        config: Monitor configuration
        auth_info: Authentication information
    """
    pid = config.process.pid
    returncode = config.process.returncode

    # Check if process exited with error
    if returncode != 0:
        logger.error(f"❌ Process {pid} exited with code {returncode}")
        await _handle_process_failure(config, returncode)
        return

    logger.info(f"✅ Process {pid} completed successfully (exit code 0)")

    # Push final changes
    await _send_final_commit(
        config.repository_path, config.branch_name, config.tool_context, auth_info
    )

    # Update task and cleanup
    task_id = (
        config.tool_context.state.get("background_task_id")
        if config.tool_context
        else None
    )

    if task_id:
        changed_files, diff_summary = await _get_diff_summary(config.tool_context)
        await _update_task_on_completion(task_id, changed_files, diff_summary)

    await _unregister_process(pid)
    log_temp_file_preserved(config.prompt_file)
    logger.info("✅ Process completed - status tracked in BackgroundTask entity")


async def _handle_periodic_updates(
    config: MonitorConfig,
    auth_info: AuthInfo,
    elapsed_time: float,
    last_push_time: float,
) -> float:
    """Handle periodic task updates and commits.

    Args:
        config: Monitor configuration
        auth_info: Authentication information
        elapsed_time: Time elapsed since start
        last_push_time: Time of last push

    Returns:
        Updated last_push_time
    """
    task_id = (
        config.tool_context.state.get("background_task_id")
        if config.tool_context
        else None
    )
    current_time = asyncio.get_event_loop().time()
    time_since_last_push = current_time - last_push_time

    # Update task progress
    if task_id and time_since_last_push >= config.progress_update_interval:
        await _update_task_progress(task_id, elapsed_time, config.process.pid)

    # Commit and push changes
    if config.tool_context and time_since_last_push >= config.commit_interval:
        commit_result = await _commit_progress(
            config.repository_path, config.branch_name, config.tool_context, auth_info
        )

        if task_id and commit_result:
            await _update_task_with_commit_info(task_id, commit_result)

        return current_time

    return last_push_time


async def _handle_process_failure(config: MonitorConfig, returncode: int) -> None:
    """Handle process failure (non-zero exit code).

    Args:
        config: Monitor configuration
        returncode: Process exit code
    """
    from services.services import get_task_service

    pid = config.process.pid
    logger.error(f"❌ Process {pid} failed with exit code {returncode}")

    # Update task to failed
    task_id = (
        config.tool_context.state.get("background_task_id")
        if config.tool_context
        else None
    )

    if task_id:
        try:
            task_service = get_task_service()
            error_message = f"Build process exited with error code {returncode}"

            # Try to get logs for more context
            log_snippet = ""
            if config.output_file:
                try:
                    with open(config.output_file, "r") as f:
                        # Get last 500 chars of log
                        f.seek(0, 2)  # Go to end
                        size = f.tell()
                        f.seek(max(0, size - 500))
                        log_snippet = f.read()
                except Exception:
                    pass

            await task_service.update_task_status(
                task_id=task_id,
                status="failed",
                message=error_message,
                progress=0,
                error=(
                    f"Process failed with exit code {returncode}\n\nLast log output:\n{log_snippet}"
                    if log_snippet
                    else error_message
                ),
            )
            logger.info(f"❌ Updated BackgroundTask {task_id} to failed")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update BackgroundTask: {e}")

    await _unregister_process(pid)
    log_temp_file_preserved(config.prompt_file)


async def _handle_process_timeout(config: MonitorConfig) -> None:
    """Handle process timeout.

    Args:
        config: Monitor configuration
    """
    pid = config.process.pid
    logger.error(
        f"⏰ Process exceeded {config.timeout_seconds} seconds, terminating... (PID: {pid})"
    )

    # Update task to failed
    task_id = (
        config.tool_context.state.get("background_task_id")
        if config.tool_context
        else None
    )

    if task_id:
        await _handle_process_timeout_task_update(task_id, config.timeout_seconds)

    await _unregister_process(pid)
    log_temp_file_preserved(config.prompt_file)
    await _terminate_process(config.process)


async def monitor_cli_process(
    process: Any,
    repository_path: str,
    branch_name: str,
    timeout_seconds: int = CLI_PROCESS_TIMEOUT,
    tool_context: Optional[ToolContext] = None,
    prompt_file: Optional[str] = None,
    output_file: Optional[str] = None,
    commit_interval: int = COMMIT_INTERVAL_DEFAULT,
    progress_update_interval: int = PROGRESS_UPDATE_INTERVAL,
) -> None:
    """Monitor CLI process with progress updates and periodic commits.

    Updates BackgroundTask entity periodically with progress.
    Streams output chunks as they arrive and saves to file.
    Commits changes at specified intervals.

    Args:
        process: The asyncio subprocess
        repository_path: Path to repository
        branch_name: Branch name
        timeout_seconds: Maximum time to wait
        tool_context: Tool context with task_id and auth info
        prompt_file: Path to temp prompt file to clean up after completion
        output_file: Path to output log file (preserved for user access)
        commit_interval: Seconds between commits
        progress_update_interval: Seconds between progress updates
    """
    config = MonitorConfig(
        process=process,
        repository_path=repository_path,
        branch_name=branch_name,
        timeout_seconds=timeout_seconds,
        tool_context=tool_context,
        prompt_file=prompt_file,
        output_file=output_file,
        commit_interval=commit_interval,
        progress_update_interval=progress_update_interval,
    )

    pid = process.pid
    logger.info(f"🔍 [{branch_name}] Monitoring CLI process started for PID {pid}")

    task_id = tool_context.state.get("background_task_id") if tool_context else None
    logger.info(f"🔍 [{branch_name}] background_task_id: {task_id}")
    logger.info(f"📤 Process output being written directly to: {output_file or 'pipe'}")

    # Extract auth info and send initial commit
    auth_info = _extract_auth_info(tool_context)
    start_time = asyncio.get_event_loop().time()
    last_push_time = (
        await _send_initial_commit(
            repository_path, branch_name, tool_context, auth_info
        )
        or start_time
    )

    # Main monitoring loop
    elapsed_time = 0
    while elapsed_time < timeout_seconds:
        try:
            # Wait for process completion
            remaining_time = min(PROCESS_CHECK_INTERVAL, timeout_seconds - elapsed_time)
            await asyncio.wait_for(process.wait(), timeout=remaining_time)

            # Process completed normally
            await _handle_normal_completion(config, auth_info)
            return

        except asyncio.TimeoutError:
            # Check if process exited silently
            if not await _is_process_running(pid):
                await _handle_normal_completion(config, auth_info)
                return

            # Process still running - update progress
            elapsed_time += remaining_time
            logger.debug(f"🔍 Process {pid} still running after {elapsed_time}s")

            last_push_time = await _handle_periodic_updates(
                config, auth_info, elapsed_time, last_push_time
            )

    # Timeout exceeded
    await _handle_process_timeout(config)
