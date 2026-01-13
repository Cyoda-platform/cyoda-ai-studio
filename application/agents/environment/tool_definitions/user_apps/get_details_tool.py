"""Tool for getting user application details."""

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
async def get_user_app_details(
    tool_context: ToolContext, env_name: str, app_name: str
) -> str:
    """Get detailed information about a specific user application deployment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with application details, or error message
    """
    # Input validation
    if not env_name or not app_name:
        return json.dumps(
            {"error": "Both env_name and app_name parameters are required."}
        )

    # Call environment management service
    user_id = tool_context.state.get("user_id", "guest")
    env_service = get_environment_management_service()
    app_details = await env_service.get_user_app_details(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
    )

    # Enrich and return result
    deployments = app_details.get("deployments", [])
    result = {
        "environment": env_name,
        "app_name": app_name,
        "deployment_count": len(deployments),
        "deployments": deployments,
    }
    return json.dumps(result)
