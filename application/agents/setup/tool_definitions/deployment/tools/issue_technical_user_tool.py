"""Tool for issuing technical user credentials."""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import UI_FUNCTION_ISSUE_TECHNICAL_USER
from ...common.formatters.deployment_formatters import format_ui_function
from ...common.utils.decorators import handle_tool_errors

logger = logging.getLogger(__name__)


@handle_tool_errors
async def ui_function_issue_technical_user(tool_context: ToolContext = None) -> str:
    """Issue M2M (machine-to-machine) technical user credentials.

    This function returns a UI function call instruction that tells the frontend
    to make an API call to issue technical user credentials (CYODA_CLIENT_ID and
    CYODA_CLIENT_SECRET) for OAuth2 authentication.

    Args:
        tool_context: Tool context (unused but required by framework)

    Returns:
        JSON string with UI function parameters for credential issuance
    """
    logger.info("Issuing technical user credentials via UI function")

    return format_ui_function(
        function_name=UI_FUNCTION_ISSUE_TECHNICAL_USER,
        method="POST",
        path="/api/users",
        response_format="json",
    )
