"""Command execution functions for repository analysis."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.repository.tools.execute_command_tool import execute_unix_command

logger = logging.getLogger(__name__)


async def _execute_and_track_command(
    command: str,
    purpose: str,
    tool_context: ToolContext,
) -> tuple[dict, dict]:
    """Execute a Unix command and track its execution.

    Args:
        command: Unix command to execute.
        purpose: Description of the command's purpose.
        tool_context: Execution context.

    Returns:
        Tuple of (command_result, command_info) where command_info tracks execution.
    """
    result = await execute_unix_command(command, tool_context)
    data = json.loads(result)

    command_info = {
        "command": command,
        "purpose": purpose,
        "success": data.get("success", False)
    }

    return data, command_info


__all__ = [
    "_execute_and_track_command",
]
