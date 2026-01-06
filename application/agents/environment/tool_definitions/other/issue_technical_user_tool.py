"""Tool for issuing M2M technical user credentials."""

from __future__ import annotations

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.hooks import creates_hook
from application.agents.shared.tool_context_helpers import get_conversation_id
from application.services.environment_management_service import get_environment_management_service
from ..common.utils.utils import require_authenticated_user, handle_tool_errors

logger = logging.getLogger(__name__)


@creates_hook("issue_technical_user")
@require_authenticated_user
@handle_tool_errors
async def issue_technical_user(tool_context: ToolContext, env_name: Optional[str] = None) -> str:
    """Issue M2M (machine-to-machine) technical user credentials.

    This function creates a hook that tells the frontend to make an API call to issue
    technical user credentials (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication.

    The hook is returned in the response and the UI renders it as a clickable button.

    Use this tool when the user asks for credentials or needs to authenticate
    their application with the Cyoda environment.

    IMPORTANT: You MUST ask the user for env_name before calling this function.
    DO NOT assume or infer the environment name. The user might have multiple environments
    (dev, staging, prod, etc.), so you must explicitly ask them which environment needs credentials.

    Args:
        tool_context: The ADK tool context (auto-injected)
        env_name: Environment name to issue credentials for. REQUIRED - must be provided by the user.
                  If not provided, this function will return an error asking you to prompt the user.
                  Example prompt: "Which environment would you like to issue credentials for?
                  For example: 'dev', 'prod', 'staging', etc."

    Returns:
        Success message with hook for UI to display credential issuance button
    """
    logger.info(f"🔧 issue_technical_user called with env_name={env_name}")

    # Get user ID and conversation ID from context
    user_id = tool_context.state.get("user_id")
    conversation_id = get_conversation_id(tool_context)
    logger.info(f"🔧 user_id from context: {user_id}")

    if not env_name:
        logger.warning("⚠️ env_name not provided to issue_technical_user")
        return (
            "ERROR: env_name parameter is required but was not provided. You MUST ask the user which "
            "environment to issue credentials for before calling this function. Ask them: 'Which environment "
            "would you like to issue credentials for? For example: dev, prod, staging, etc.' "
            "DO NOT assume or infer the environment name."
        )

    # Construct environment URL using the same pattern as other functions
    client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
    env_service = get_environment_management_service()
    normalized_user = env_service._normalize_for_namespace(user_id)
    normalized_env = env_service._normalize_for_namespace(env_name)
    namespace = f"client-{normalized_user}-{normalized_env}"
    env_url = f"{namespace}.{client_host}"
    logger.info(f"🔧 Constructed env_url: {env_url}")

    # Create hook for issuing technical user
    from application.agents.shared.hooks import (
        create_issue_technical_user_hook,
        wrap_response_with_hook,
    )

    hook = create_issue_technical_user_hook(
        conversation_id=conversation_id,
        env_url=env_url,
    )

    # Store hook in context for SSE streaming
    tool_context.state["last_tool_hook"] = hook

    success_msg = (
        f"✅ Credential issuance initiated for environment: {env_url}\n\n"
        "Click the button below to create your M2M technical user credentials "
        "(CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication."
    )
    logger.info(f"🔧 Returning success message with hook for {env_url}")
    return wrap_response_with_hook(success_msg, hook)
