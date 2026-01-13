"""Tool for scaling user application deployments."""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from application.services.core.resource_limit_service import get_resource_limit_service
from application.services.environment_management_service import (
    get_environment_management_service,
)

from ..common.utils.utils import handle_tool_errors, require_authenticated_user

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def scale_user_app(
    tool_context: ToolContext,
    env_name: str,
    app_name: str,
    deployment_name: str,
    replicas: int,
) -> str:
    """Scale a user application deployment to a specific number of replicas.

    Enforces resource limits via ResourceLimitService.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        deployment_name: Name of the deployment within the app namespace to scale
        replicas: Number of replicas to scale to (must be >= 0, max configured limit)

    Returns:
        JSON string with scaling result, or error message
    """
    # Input validation
    if not env_name or not app_name or not deployment_name:
        return json.dumps(
            {
                "error": "env_name, app_name, and deployment_name parameters are required."
            }
        )

    user_id = tool_context.state.get("user_id", "guest")

    # Check resource limits (business logic that should stay in tool layer)
    limit_service = get_resource_limit_service()
    limit_check = limit_service.check_replica_limit(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
        requested_replicas=replicas,
    )

    if not limit_check.allowed:
        error_msg = limit_service.format_limit_error(limit_check)
        logger.warning(
            f"Scale operation denied for user={user_id}: {limit_check.reason}"
        )
        return json.dumps(
            {
                "error": limit_check.reason,
                "limit": limit_check.limit_value,
                "requested": limit_check.current_value,
                "message": error_msg,
            }
        )

    # Call environment management service
    env_service = get_environment_management_service()
    scale_result = await env_service.scale_user_app(
        user_id=user_id,
        env_name=env_name,
        app_name=app_name,
        deployment_name=deployment_name,
        replicas=replicas,
    )

    # Return result
    return json.dumps(scale_result)
