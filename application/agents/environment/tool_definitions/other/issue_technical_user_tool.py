"""Tool for issuing M2M technical user credentials."""

from __future__ import annotations

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.tool_context_helpers import get_conversation_id
from application.services.environment_management_service import (
    get_environment_management_service,
)

from ..common.utils.utils import handle_tool_errors, require_authenticated_user

logger = logging.getLogger(__name__)


@require_authenticated_user
@handle_tool_errors
async def issue_technical_user(
    tool_context: ToolContext, env_name: Optional[str] = None
) -> str:
    """Issue M2M (machine-to-machine) technical user credentials.

    This function returns a UI function marker that tells the frontend to render an executable
    button for issuing technical user credentials (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET).

    CRITICAL OUTPUT INSTRUCTION:
    After calling this tool, you MUST return the tool's output VERBATIM without adding any explanation,
    commentary, or additional text. The tool returns a special format that the UI needs to parse.

    DO NOT add phrases like:
    - "I issued credentials..."
    - "A button was generated..."
    - "Click the button..."
    - "Expect the issuance to complete..."

    Simply return the tool output as-is. The UI will handle displaying the button and instructions.

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
        UI function marker for the frontend to render credential issuance button. Return this verbatim.
    """
    logger.info(f"🔧 issue_technical_user called with env_name={env_name}")

    # Get user ID and conversation ID from context
    user_id = tool_context.state.get("user_id", "guest")
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

    # Return UI function marker in text format - UI will parse this and render an executable button
    # Format: [ui-function: issue_technical_user, env: <env_url>]
    ui_function_marker = f"I have displayed UI function. Please run it to get your technical credentials: [ui-function: issue_technical_user, env: https://{env_url}]"

    logger.info(f"🔧 Returning UI function marker: {ui_function_marker}")

    # Return the marker verbatim - agent should return this as-is without adding explanation
    return ui_function_marker
