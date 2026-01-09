"""Tool for deleting environments."""

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
async def delete_environment(tool_context: ToolContext, env_name: str) -> str:
    """Delete an environment (namespace) and all its resources.

    WARNING: This is a destructive operation that will delete the entire environment
    including all applications, data, and configurations. Use with caution.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to delete

    Returns:
        JSON string with deletion result
    """
    # Validate input
    if not env_name:
        return json.dumps({"error": "env_name parameter is required."})

    # Call environment management service
    user_id = tool_context.state.get("user_id", "guest")
    env_service = get_environment_management_service()
    deletion_result = await env_service.delete_environment(
        user_id=user_id, env_name=env_name
    )

    return json.dumps(deletion_result)
