"""Tool for retrieving build ID from context."""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import KEY_BUILD_ID
from ...common.utils.decorators import handle_tool_errors

logger = logging.getLogger(__name__)


@handle_tool_errors
async def get_build_id_from_context(tool_context: ToolContext) -> str:
    """Retrieve build ID from the current session context.

    In the deprecated workflow system, this function retrieved the build ID from
    the deployment workflow entity. In the ADK version, we check the session state
    for a stored build_id value.

    Args:
        tool_context: Tool context containing session state

    Returns:
        Build ID string if found, otherwise a message indicating it's not available
    """
    session_state = tool_context.state
    build_id = session_state.get(KEY_BUILD_ID)

    if build_id:
        logger.info(f"Retrieved build_id from session: {build_id}")
        return build_id

    logger.warning("No build_id found in session state")
    return "Build ID not found in session. Please provide your build ID manually or check your deployment status."
