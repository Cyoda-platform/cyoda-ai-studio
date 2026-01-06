"""Shared CLI process initialization logic.

Consolidates common logic for starting and monitoring CLI processes
(code generation, application builds, etc.) to follow DRY principle.
"""

import asyncio
import logging
import os
from typing import Any, Optional

from application.agents.shared.process_manager import get_process_manager
from application.agents.shared.repository_tools.monitoring import _terminate_process
from common.config.config import CLI_PROVIDER

logger = logging.getLogger(__name__)


async def start_cli_process(
    command: list[str],
    repository_path: str,
    process_type: str = "codegen",
    stdout_fd: Optional[int] = None,
    stderr_fd: Optional[int] = None,
) -> tuple[bool, str, Optional[Any]]:
    """Start a CLI process with process limit checking and registration.

    Unified function for starting CLI subprocesses (code generation, builds).
    Works with both script-based (code generation) and direct command execution (builds).

    Handles:
    - Process manager limits
    - Subprocess creation from command list
    - Process registration
    - Error handling

    Args:
        command: Command list to execute (e.g., ["bash", "script.sh", "arg1", ...])
        repository_path: Repository path (working directory)
        process_type: Type of process for logging (codegen, build, etc.)
        stdout_fd: Optional file descriptor for stdout redirection
        stderr_fd: Optional file descriptor for stderr redirection

    Returns:
        Tuple of (success, error_msg, process) where process is None on failure
    """
    # Step 1: Check process limit
    process_manager = get_process_manager()
    if not await process_manager.can_start_process():
        active_count = await process_manager.get_active_count()
        return (
            False,
            f"ERROR: Cannot start {process_type}: maximum concurrent processes "
            f"({active_count}) reached. Please wait for existing processes to complete.",
            None,
        )

    # Step 2: Start subprocess
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=stdout_fd or asyncio.subprocess.DEVNULL,
            stderr=stderr_fd or asyncio.subprocess.DEVNULL,
            cwd=repository_path,
        )
        # Close file descriptors in parent process if provided
        if stdout_fd:
            os.close(stdout_fd)
        if stderr_fd:
            os.close(stderr_fd)
    except Exception as e:
        if stdout_fd:
            os.close(stdout_fd)
        if stderr_fd:
            os.close(stderr_fd)
        error_msg = f"Failed to start {process_type} process: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None

    logger.info(
        f"✅ {CLI_PROVIDER.capitalize()} {process_type} process started with PID: {process.pid}"
    )

    # Step 3: Register process with manager
    if not await process_manager.register_process(process.pid):
        await _terminate_process(process)
        return (
            False,
            f"ERROR: Cannot start {process_type}: process limit exceeded.",
            None,
        )

    return True, "", process


async def setup_and_monitor_cli_process(
    process: Any,
    repository_path: str,
    branch_name: str,
    tool_context: Any,
    setup_tracking_fn,
    start_monitoring_fn,
    process_type: str = "codegen",
    **tracking_kwargs,
) -> tuple[bool, str, Optional[str], Optional[str]]:
    """Setup task tracking and monitoring for a CLI process.

    Unified function for post-process setup (task creation, monitoring).
    Handles:
    - Task creation and tracking
    - Background monitoring setup
    - Logging

    Args:
        process: Running process object
        repository_path: Repository path
        branch_name: Git branch name
        tool_context: Tool context for state management
        setup_tracking_fn: Function to create and track task (returns task_id, env_task_id)
        start_monitoring_fn: Function to start monitoring the process
        process_type: Type of process (codegen, build, etc.)
        **tracking_kwargs: Additional arguments for setup_tracking_fn

    Returns:
        Tuple of (success, error_msg, task_id, env_task_id)
    """
    try:
        # Step 1: Setup task tracking
        task_id, env_task_id = await setup_tracking_fn(
            tool_context, branch_name, process.pid, **tracking_kwargs
        )
        logger.info(
            f"✅ {process_type.capitalize()} task created (Task: {task_id}, Env: {env_task_id})"
        )

        # Step 2: Start background monitoring
        await start_monitoring_fn(process, repository_path, branch_name, tool_context)
        logger.info(f"✅ Background monitoring started for {process_type} process {process.pid}")

        return True, "", task_id, env_task_id

    except Exception as e:
        error_msg = f"Failed to setup {process_type} tracking: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None, None
