"""Tool for scaling application deployments."""

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
async def scale_application(
    tool_context: ToolContext, env_name: str, app_name: str, replicas: int
) -> str:
    """Scale an application deployment to a specific number of replicas.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        replicas: Number of replicas to scale to (must be >= 0)

    Returns:
        JSON string with scaling result, or error message
    """
    # 1. Input validation
    user_id = tool_context.state.get("user_id", "guest")

    if not env_name or not app_name:
        return json.dumps(
            {"error": "Both env_name and app_name parameters are required."}
        )

    if replicas < 0:
        return json.dumps({"error": "Replicas must be >= 0."})

    # 2. Call environment management service
    env_service = get_environment_management_service()
    scale_result = await env_service.scale_application(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
        replicas=replicas,
    )

    # 3. Return result
    return json.dumps(scale_result)
