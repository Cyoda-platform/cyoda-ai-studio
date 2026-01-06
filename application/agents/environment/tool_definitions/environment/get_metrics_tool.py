"""Tool for getting environment metrics."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def get_environment_metrics(tool_context: ToolContext, env_name: str) -> str:
    """Get pod metrics (CPU and memory usage) for an environment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name

    Returns:
        JSON string with metrics data, or error message
    """
    # 1. Input validation
    user_id = tool_context.state.get("user_id")

    if not env_name:
        return json.dumps({"error": "env_name parameter is required."})

    # 2. Call environment management service
    env_service = get_environment_management_service()
    metrics_data = await env_service.get_environment_metrics(
        user_id=user_id,
        env_name=env_name,
    )

    # 3. Return result
    return json.dumps(metrics_data)
