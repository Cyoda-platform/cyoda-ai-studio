"""Process management for CLI code generation.

This module handles starting CLI processes, registering them with the process
manager, creating background tasks, and setting up monitoring.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from application.agents.github.tool_definitions.code_generation.helpers import (
    _create_background_task,
    _create_output_log_file,
    _rename_output_file_with_pid,
    _start_monitoring_task,
)
from application.agents.github.tool_definitions.common.constants import (
    CLI_PROCESS_TIMEOUT,
    COMMIT_INTERVAL_DEFAULT,
    PROGRESS_UPDATE_INTERVAL,
)

logger = logging.getLogger(__name__)


async def _start_and_register_process(
    context, script_path: Path, cli_model: str, prompt_file: str
) -> tuple[bool, str, Optional[object], Optional[str]]:
    """Start CLI process and register with process manager.

    Args:
        context: CLI context
        script_path: Path to CLI script
        cli_model: CLI model name
        prompt_file: Path to prompt file

    Returns:
        Tuple of (success, error_msg, process, output_file)
    """
    # Create output file for logging
    success, error_msg, output_file, output_fd = _create_output_log_file(
        context.branch_name, "codegen"
    )
    if not success:
        if output_fd:
            os.close(output_fd)
        return False, error_msg, None, None

    # Build command for _start_cli_process
    command = [
        "bash",
        str(script_path.absolute()),
        f"@{prompt_file}",
        cli_model,
        context.repository_path,
        context.branch_name,
    ]

    # Use shared CLI process starter with output fd
    from application.agents.shared.repository_tools.cli_process import start_cli_process

    success, error_msg, process = await start_cli_process(
        command=command,
        repository_path=context.repository_path,
        process_type="codegen",
        stdout_fd=output_fd,
    )
    if not success or not process:
        return False, error_msg or "Failed to start code generation", None, None

    # Rename output file with PID
    output_file = _rename_output_file_with_pid(
        output_file, context.branch_name, process.pid, "codegen"
    )

    logger.info(f"📋 Output log: {output_file}")

    return True, "", process, output_file


async def _setup_codegen_tracking(
    tool_context, branch_name: str, process_pid: int, **kwargs
) -> tuple[Optional[str], Optional[str]]:
    """Wrapper to convert _create_background_task to setup_and_monitor signature.

    Args:
        tool_context: Tool context
        branch_name: Branch name
        process_pid: Process ID
        **kwargs: Additional arguments (context, output_file, user_request, language, conversation_id)

    Returns:
        Tuple of (task_id, None) - env_task_id is None for code generation
    """
    context = kwargs.get("context")
    output_file = kwargs.get("output_file")
    user_request = kwargs.get("user_request", "")

    task_id = await _create_background_task(
        context=context,
        task_type="code_generation",
        task_name=f"Generate code: {user_request[:50]}...",
        task_description=f"Generating code with CLI: {user_request[:200]}...",
        process_pid=process_pid,
        output_file=output_file,
    )
    tool_context.state["code_gen_process_pid"] = process_pid
    return task_id, None  # No env_task_id for code generation


async def _create_and_setup_background_task(
    context, process, prompt_file: str, output_file: str, user_request: str
) -> tuple[Optional[str], Optional[dict]]:
    """Create background task and hook for monitoring code generation.

    Args:
        context: CLI context
        process: Running process object
        prompt_file: Path to prompt file
        output_file: Path to output log file
        user_request: Original user request

    Returns:
        Tuple of (task_id, hook)
    """
    from application.agents.shared.repository_tools import setup_and_monitor_cli_process

    # Define async wrapper for monitoring to properly await the coroutine
    async def start_monitoring_wrapper(p, rp, bn, tc):
        """Wrapper to properly await the async monitoring task."""
        return await _start_monitoring_task(
            process=p,
            context=context,
            prompt_file=prompt_file,
            output_file=output_file,
            timeout_seconds=CLI_PROCESS_TIMEOUT,
            commit_interval=COMMIT_INTERVAL_DEFAULT,
            progress_update_interval=PROGRESS_UPDATE_INTERVAL,
        )

    # Use shared setup function
    success, error_msg, task_id, _ = await setup_and_monitor_cli_process(
        process=process,
        repository_path=context.repository_path,
        branch_name=context.branch_name,
        tool_context=context.tool_context,
        setup_tracking_fn=_setup_codegen_tracking,
        start_monitoring_fn=start_monitoring_wrapper,
        process_type="codegen",
        context=context,
        output_file=output_file,
        user_request=user_request,
        language=context.language,
        conversation_id=context.conversation_id,
    )

    if not success:
        logger.error(f"Failed to setup code generation tracking: {error_msg}")
        return None, None

    # Hooks removed - UI auto-detects code generation operations
    return task_id, None
