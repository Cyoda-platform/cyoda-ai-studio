"""Process monitoring for code generation."""

from __future__ import annotations

import logging
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import (
    CLI_PROCESS_TIMEOUT,
    COMMIT_INTERVAL_DEFAULT,
    PROGRESS_UPDATE_INTERVAL,
    TRUNCATE_LENGTH_MEDIUM,
)

logger = logging.getLogger(__name__)


async def monitor_code_generation_process(
    process: Any,
    repository_path: str,
    branch_name: str,
    user_request: str,
    timeout_seconds: int = CLI_PROCESS_TIMEOUT,
    tool_context: Optional[ToolContext] = None,
    prompt_file: Optional[str] = None,
    output_file: Optional[str] = None,
) -> None:
    """
    Wrapper for code generation process monitoring.
    Delegates to unified _monitor_cli_process function.

    Args:
        process: The asyncio subprocess
        repository_path: Path to repository
        branch_name: Branch name
        user_request: User's code generation request (for logging)
        timeout_seconds: Maximum time to wait (default: CLI_PROCESS_TIMEOUT = 1 hour)
        tool_context: Tool context with task_id
        prompt_file: Path to temp prompt file to clean up after completion
        output_file: Path to output log file (preserved for user access)
    """
    logger.info(f"🔍 [{branch_name}] Code generation request: {user_request[:TRUNCATE_LENGTH_MEDIUM]}...")

    # Import from tools.py - this will be extracted later in Phase 6
    from application.agents.github.tools import _monitor_cli_process

    await _monitor_cli_process(
        process=process,
        repository_path=repository_path,
        branch_name=branch_name,
        timeout_seconds=timeout_seconds,
        tool_context=tool_context,
        prompt_file=prompt_file,
        output_file=output_file,
        commit_interval=COMMIT_INTERVAL_DEFAULT,
        progress_update_interval=PROGRESS_UPDATE_INTERVAL,
    )
