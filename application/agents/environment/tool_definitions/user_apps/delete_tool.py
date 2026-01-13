"""Tool for deleting user applications."""

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
async def delete_user_app(
    tool_context: ToolContext, env_name: str, app_name: str
) -> str:
    """Delete a user application namespace and all its resources.

    WARNING: This is a destructive operation that will delete the entire user application
    namespace including all deployments, data, and configurations.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name to delete

    Returns:
        JSON string with deletion result, or error message
    """
    # Input validation
    if not env_name or not app_name:
        return json.dumps(
            {"error": "Both env_name and app_name parameters are required."}
        )

    # Call environment management service
    user_id = tool_context.state.get("user_id", "guest")
    env_service = get_environment_management_service()
    deletion_result = await env_service.delete_user_app(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
    )

    # Return result
    return json.dumps(deletion_result)
