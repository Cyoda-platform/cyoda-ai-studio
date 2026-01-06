"""Tool for validating environment variables."""

from __future__ import annotations

import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import DEFAULT_ENV_VARS
from ...common.formatters.validation_formatters import format_validation_result
from ...common.utils.decorators import handle_tool_errors


@handle_tool_errors
async def validate_environment(
    required_vars: Optional[list[str]] = None,
    tool_context: ToolContext = None,
) -> str:
    """Validate that required environment variables are set.

    Checks if the specified environment variables are configured.
    Useful for verifying Cyoda project setup.

    Args:
        required_vars: List of environment variable names to check.
                       Defaults to common Cyoda variables.
        tool_context: Tool context (unused but required by framework)

    Returns:
        JSON string mapping variable names to their presence status (True/False)
    """
    if required_vars is None:
        required_vars = DEFAULT_ENV_VARS

    result = {var: os.getenv(var) is not None for var in required_vars}

    return format_validation_result(result)
