"""Tool for marking setup discussion as finished."""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

from ...common.utils.decorators import handle_tool_errors

logger = logging.getLogger(__name__)


@handle_tool_errors
async def finish_discussion(tool_context: ToolContext = None) -> str:
    """Mark the setup discussion as finished.

    This function signals that the setup process is complete and the user
    is ready to proceed with development.

    Args:
        tool_context: Tool context (unused but required by framework)

    Returns:
        Success message indicating setup is complete
    """
    logger.info("Setup discussion marked as finished")
    return (
        "Setup complete! You're all set to start developing your Cyoda "
        "application. If you need any further assistance, feel free to ask."
    )
