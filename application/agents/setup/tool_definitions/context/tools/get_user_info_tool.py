"""Tool for retrieving comprehensive user and workflow information."""

from __future__ import annotations

import logging

import httpx
from google.adk.tools.tool_context import ToolContext

from ...common.constants.config import config
from ...common.constants.constants import GUEST_USER_PREFIX, KEY_USER_ID
from ...common.formatters.context_formatters import format_user_info
from ...common.utils.decorators import handle_tool_errors
from ..helpers._conversation_helper import get_workflow_cache

logger = logging.getLogger(__name__)


async def check_environment_deployed(cyoda_url: str) -> bool:
    """Check if Cyoda environment is deployed by attempting to access it.

    Args:
        cyoda_url: URL of the Cyoda environment

    Returns:
        True if environment exists (returns 401), False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{cyoda_url}/api/v1",
                headers={"Authorization": "Bearer guest_token"},
            )
            # If we get 401 (invalid token), environment exists
            return response.status_code == 401
    except httpx.HTTPStatusError as e:
        return e.response.status_code == 401
    except Exception as e:
        logger.debug(f"Could not check Cyoda environment status: {e}")
        return False


@handle_tool_errors
async def get_user_info(
    user_request: str,
    tool_context: ToolContext,
) -> str:
    """Retrieve comprehensive user and workflow information from entity and workflow cache.

    This function collects all available information about the user's current context including:
    - User authentication status and Cyoda environment details
    - Repository information (branch, name, URL, installation ID)
    - Programming language and workflow settings
    - Build and deployment status
    - User requests and file attachments
    - Any other cached workflow data

    Args:
        user_request: The user's request or query for context
        tool_context: Tool context containing session state

    Returns:
        Formatted string with comprehensive user and workflow information
    """
    session_state = tool_context.state
    user_id = session_state.get(KEY_USER_ID, "guest.user")

    # Check if user is guest
    is_guest = user_id.startswith(GUEST_USER_PREFIX)

    # Determine Cyoda environment URL and deployment status
    if is_guest:
        cyoda_url = "please, log in to deploy"
        deployed = False
    else:
        cyoda_url = config.get_client_url(user_id)
        deployed = await check_environment_deployed(cyoda_url)

    # Build info dictionary with user authentication and environment information
    info = {
        "user_logged_in_most_recent_status": not is_guest,
        "user_id": user_id,
        "cyoda_env_most_recent_url": cyoda_url,
        "cyoda_environment_most_recent_status": "deployed" if deployed else "is not yet deployed",
    }

    # Try to get workflow_cache from Conversation entity and merge all data
    workflow_cache = await get_workflow_cache(tool_context)
    info.update(workflow_cache)

    # Return formatted user info
    return format_user_info(
        user_logged_in=not is_guest,
        user_id=user_id,
        cyoda_url=cyoda_url,
        cyoda_status="deployed" if deployed else "is not yet deployed",
        **workflow_cache,
    )
