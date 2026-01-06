"""Tool for checking if a Cyoda environment exists."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from common.exception.exceptions import InvalidTokenException

from application.agents.shared.hooks import (
    creates_hook,
    create_cloud_window_hook,
    wrap_response_with_hook,
)
from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


def _construct_environment_url(user_id: str, env_name: str) -> str:
    """Construct environment URL from user ID and environment name.

    Args:
        user_id: User ID
        env_name: Environment name

    Returns:
        Environment URL
    """
    client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
    env_service = get_environment_management_service()
    normalized_user = env_service._normalize_for_namespace(user_id)
    normalized_env = env_service._normalize_for_namespace(env_name)
    namespace = f"client-{normalized_user}-{normalized_env}"
    return f"https://{namespace}.{client_host}"


def _create_environment_hook(
        conversation_id: Optional[str],
        url: str,
        status: str,
        message: str,
        tool_context: ToolContext,
) -> Optional[dict]:
    """Create and store cloud window hook.

    Args:
        conversation_id: Conversation ID
        url: Environment URL
        status: Environment status
        message: Hook message
        tool_context: Tool context

    Returns:
        Hook dictionary or None
    """
    if not conversation_id:
        return None

    hook = create_cloud_window_hook(
        conversation_id=conversation_id,
        environment_url=url,
        environment_status=status,
        message=message,
    )
    tool_context.state["last_tool_hook"] = hook
    return hook


@creates_hook("cloud_window")
@require_authenticated_user
@handle_tool_errors
async def check_environment_exists(tool_context: ToolContext, env_name: str) -> str:
    """Check if a Cyoda environment exists for the current user.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to check (REQUIRED - e.g., 'dev', 'prod', 'staging')

    Returns:
        JSON string with environment status and hook

    Raises:
        ValueError: If env_name is not provided or is empty
    """
    # Validate input
    if not env_name or not env_name.strip():
        raise ValueError(
            "The 'env_name' parameter is required but was not provided. "
            "You MUST ask the user which environment to check before calling this function. "
            "Ask them: 'Which environment would you like to check? "
            "For example: dev, prod, staging, etc.' DO NOT assume or infer the environment name."
        )

    # Get context info
    user_id = tool_context.state.get("user_id")
    conversation_id = tool_context.state.get("conversation_id")

    # Construct URL
    url = _construct_environment_url(user_id, env_name)

    # Check environment API
    # Note: Import is at module level to satisfy IDE, but tests patch common.utils.utils.send_get_request
    from common.utils.utils import send_get_request  # noqa: F401 (imported for usage below)

    try:
        await send_get_request(api_url=url, path="api/v1", token="guest_token")
        # If we get here without exception, status is unclear
        exists = False
        status = "unknown"
        message = f"Environment status unclear for {url}"
        hook_message = "Check your environment status in the Cloud panel."

    except InvalidTokenException:
        # InvalidTokenException means the environment exists and is responding
        logger.info(f"Environment exists for user {user_id}: {url}")
        exists = True
        status = "deployed"
        message = f"Your Cyoda environment is deployed and accessible at {url}"
        hook_message = "Your environment is ready! View details in the Cloud panel."

    except Exception as e:
        # Any other exception means environment is not deployed
        logger.info(f"Environment not deployed for user {user_id}: {e}")
        exists = False
        status = "not_deployed"
        message = f"No Cyoda environment found at {url}. You can deploy one using deploy_cyoda_environment()."
        hook_message = "No environment found. Deploy one from the Cloud panel."

    result = {"exists": exists, "url": url, "message": message}

    # Create hook
    hook = _create_environment_hook(conversation_id, url, status, hook_message, tool_context)

    # Return response with hook if available
    if hook:
        return wrap_response_with_hook(message, hook)

    return json.dumps(result)
