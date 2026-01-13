"""Tool for getting environment pods."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import (
    get_environment_management_service,
)

from ..common.utils.utils import handle_tool_errors, require_authenticated_user

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def get_environment_pods(tool_context: ToolContext, env_name: str) -> str:
    """Get all pods running in an environment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name

    Returns:
        JSON string with pod list, or error message
    """
    # 1. Input validation
    user_id = tool_context.state.get("user_id", "guest")

    if not env_name:
        return json.dumps({"error": "env_name parameter is required."})

    # 2. Call environment management service
    env_service = get_environment_management_service()
    pods_info = await env_service.get_environment_pods(
        user_id=user_id,
        env_name=env_name,
    )

    # 3. Return result
    return json.dumps(pods_info)
