"""Tool for describing environment deployments."""

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
async def describe_environment(tool_context: ToolContext, env_name: str) -> str:
    """Describe a Cyoda environment by listing all platform deployments in it.

    This shows the Cyoda platform services running in the environment namespace
    (client-{user}-{env}), NOT user applications which run in separate namespaces.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to describe

    Returns:
        JSON string with list of Cyoda platform deployments and their details, or error message
    """
    # 1. Input validation
    user_id = tool_context.state.get("user_id", "guest")

    if not env_name:
        return json.dumps({"error": "env_name parameter is required."})

    # 2. Call environment management service
    env_service = get_environment_management_service()
    environment_info = await env_service.describe_environment(
        user_id=user_id, env_name=env_name
    )

    # 3. Return result
    return json.dumps(environment_info)
