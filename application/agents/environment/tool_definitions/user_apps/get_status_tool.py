"""Tool for getting user application deployment status."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def get_user_app_status(tool_context: ToolContext, env_name: str, app_name: str, deployment_name: str) -> str:
    """Get the deployment status and health of a user application.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        deployment_name: Deployment name

    Returns:
        JSON string with status information, or error message
    """
    # Input validation
    if not env_name or not app_name or not deployment_name:
        return json.dumps({"error": "env_name, app_name, and deployment_name parameters are required."})

    # Call environment management service
    user_id = tool_context.state.get("user_id")
    env_service = get_environment_management_service()
    status_info = await env_service.get_user_app_status(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
        deployment_name=deployment_name,
    )

    # Return result
    return json.dumps(status_info)
