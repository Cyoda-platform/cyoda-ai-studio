"""Tool for restarting user application deployments."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def restart_user_app(tool_context: ToolContext, env_name: str, app_name: str, deployment_name: str) -> str:
    """Restart a user application deployment by triggering a rollout restart.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        deployment_name: Name of the deployment within the app namespace to restart

    Returns:
        JSON string with restart result, or error message
    """
    # Input validation
    if not env_name or not app_name or not deployment_name:
        return json.dumps({"error": "env_name, app_name, and deployment_name parameters are required."})

    # Call environment management service
    user_id = tool_context.state.get("user_id")
    env_service = get_environment_management_service()
    restart_result = await env_service.restart_user_app(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
        deployment_name=deployment_name,
    )

    # Return result
    return json.dumps(restart_result)
