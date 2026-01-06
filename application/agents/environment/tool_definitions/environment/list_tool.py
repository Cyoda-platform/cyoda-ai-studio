"""Tool for listing user's Cyoda environments."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def list_environments(tool_context: ToolContext) -> str:
    """List all Cyoda environments for the current user.

    Returns a list of all environments (namespaces) that belong to the user,
    with their status and creation timestamp.

    Args:
        tool_context: The ADK tool context

    Returns:
        JSON string with list of environments: {"environments": [...], "count": N}, or error message
    """
    # 1. Input validation
    user_id = tool_context.state.get("user_id")

    # 2. Call environment management service
    env_service = get_environment_management_service()
    user_environments = await env_service.list_environments(user_id=user_id)

    # 3. Format and return result
    result = {
        "environments": user_environments,
        "count": len(user_environments),
    }
    return json.dumps(result)
