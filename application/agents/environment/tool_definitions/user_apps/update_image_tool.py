"""Tool for updating user application container images."""

from __future__ import annotations

import json
import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def update_user_app_image(
        tool_context: ToolContext,
        env_name: str,
        app_name: str,
        deployment_name: str,
        image: str,
        container: Optional[str] = None
) -> str:
    """Update the container image of a user application deployment (rollout update).

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        deployment_name: Name of the deployment within the app namespace
        image: New container image (e.g., "myapp:v2.0")
        container: Optional container name (if deployment has multiple containers)

    Returns:
        JSON string with update result, or error message
    """
    # Input validation
    if not env_name or not app_name or not deployment_name or not image:
        return json.dumps({"error": "env_name, app_name, deployment_name, and image parameters are required."})

    # Call environment management service
    user_id = tool_context.state.get("user_id")
    env_service = get_environment_management_service()
    update_result = await env_service.update_user_app_image(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
        deployment_name=deployment_name,
        image=image,
        container=container,
    )

    # Return result
    return json.dumps(update_result)
