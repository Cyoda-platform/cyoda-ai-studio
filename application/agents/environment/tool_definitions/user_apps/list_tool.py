"""Tool for listing user applications."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def list_user_apps(tool_context: ToolContext, env_name: str) -> str:
    """List all user applications in an environment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name

    Returns:
        JSON string with list of user applications, or error message
    """
    # Input validation
    if not env_name:
        return json.dumps({"error": "env_name parameter is required."})

    # Call environment management service
    user_id = tool_context.state.get("user_id")
    env_service = get_environment_management_service()
    user_apps = await env_service.list_user_apps(
        user_id=user_id,
        env_name=env_name,
    )

    # Wrap result in standard format
    result = {"user_applications": user_apps}
    return json.dumps(result)
