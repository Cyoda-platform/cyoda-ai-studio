"""Tool for getting user application pods."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def get_user_app_pods(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Get all pods running in a user application namespace.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with pod list, or error message
    """
    # Input validation
    if not env_name or not app_name:
        return json.dumps({"error": "Both env_name and app_name parameters are required."})

    # Call environment management service
    user_id = tool_context.state.get("user_id")
    env_service = get_environment_management_service()
    pods_info = await env_service.get_user_app_pods(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
    )

    # Return result
    return json.dumps(pods_info)
