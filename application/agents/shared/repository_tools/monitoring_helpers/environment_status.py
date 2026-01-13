"""Environment status checking for Cyoda deployments.

This module handles checking if user environments are deployed and accessible.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from common.exception.exceptions import InvalidTokenException
from common.utils.utils import send_get_request

logger = logging.getLogger(__name__)

# Environment status constants
DEFAULT_CLIENT_HOST = "cyoda.cloud"
GUEST_USER_PREFIX = "guest."
MOCK_MODE_ENV_VAR = "MOCK_ENVIRONMENT_CHECK"
NO_TOOL_CONTEXT_ERROR = "ERROR: tool_context not available"
NEEDS_LOGIN_STATUS = (
    "NEEDS_LOGIN: User is not logged in. Please log in to deploy a Cyoda environment."
)
DEPLOYED_STATUS_TEMPLATE = "DEPLOYED: Your Cyoda environment is already deployed at {url}. Ready to build your application."
NOT_DEPLOYED_STATUS_TEMPLATE = (
    "NOT_DEPLOYED: Your Cyoda environment is not yet deployed. URL will be: {url}"
)
DEPLOYING_STATUS_TEMPLATE = (
    "DEPLOYING: Your Cyoda environment deployment is in progress "
    "(Build ID: {build_id}, Namespace: {namespace}). "
    "Deployment typically takes 5-10 minutes. "
    "Your application build has already started and will be ready when deployment completes."
)
ERROR_STATUS_TEMPLATE = "ERROR: Failed to check environment status: {error}"


class EnvironmentStatusContext(BaseModel):
    """Context for environment status check."""

    user_id: str
    is_guest: bool
    deployment_started: bool
    deployment_build_id: Optional[str] = None
    deployment_namespace: Optional[str] = None
    is_mock_mode: bool = False


def _extract_status_context(tool_context: ToolContext) -> EnvironmentStatusContext:
    """Extract environment status context from tool context.

    Args:
        tool_context: The ADK tool context

    Returns:
        EnvironmentStatusContext with extracted values
    """
    user_id = tool_context.state.get("user_id", "guest")
    is_guest = user_id.startswith(GUEST_USER_PREFIX)
    deployment_started = tool_context.state.get("deployment_started", False)
    deployment_build_id = tool_context.state.get("deployment_build_id")
    deployment_namespace = tool_context.state.get("deployment_namespace")
    is_mock_mode = os.getenv(MOCK_MODE_ENV_VAR, "false").lower() == "true"

    return EnvironmentStatusContext(
        user_id=user_id,
        is_guest=is_guest,
        deployment_started=deployment_started,
        deployment_build_id=deployment_build_id,
        deployment_namespace=deployment_namespace,
        is_mock_mode=is_mock_mode,
    )


def _construct_environment_url(user_id: str) -> str:
    """Construct the environment URL from user ID.

    Args:
        user_id: The user ID

    Returns:
        Constructed environment URL
    """
    client_host = os.getenv("CLIENT_HOST", DEFAULT_CLIENT_HOST)
    return f"https://client-{user_id.lower()}.{client_host}"


def _store_environment_info(
    tool_context: ToolContext, url: str, deployed: bool
) -> None:
    """Store environment info in tool context state.

    Args:
        tool_context: The ADK tool context
        url: Environment URL
        deployed: Whether environment is deployed
    """
    tool_context.state["cyoda_env_url"] = url
    tool_context.state["cyoda_env_deployed"] = deployed


async def _check_environment_deployed(url: str, user_id: str) -> bool:
    """Check if environment is deployed by calling its API.

    Args:
        url: Environment URL to check
        user_id: User ID (for logging)

    Returns:
        True if environment is deployed, False otherwise
    """
    try:
        await send_get_request(api_url=url, path="api/v1", token="guest_token")
    except InvalidTokenException:
        # InvalidTokenException means the environment exists and is responding
        logger.info(f"✅ Environment deployed for user {user_id}: {url}")
        return True
    except Exception as e:
        logger.info(f"Environment not deployed for user {user_id}: {e}")
        return False


async def check_user_environment_status(
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Check if the user's Cyoda environment is deployed and ready.

    This function automatically checks the deployment status without requiring
    user confirmation. It returns structured information about the environment.

    Args:
        tool_context: Execution context (auto-injected)

    Returns:
        Status message indicating if environment is deployed or needs deployment

    Example:
        >>> status = await check_user_environment_status(tool_context=context)
        >>> print(status)
    """
    try:
        # Step 1: Validate tool context
        if not tool_context:
            return NO_TOOL_CONTEXT_ERROR

        # Step 2: Extract status context
        context = _extract_status_context(tool_context)

        # Step 3: Handle mock mode
        if context.is_mock_mode:
            logger.info(
                f"Mock mode enabled - returning DEPLOYED for user {context.user_id}"
            )
            url = _construct_environment_url(context.user_id)
            _store_environment_info(tool_context, url, True)
            return DEPLOYED_STATUS_TEMPLATE.format(url=url)

        # Step 4: Handle guest users
        if context.is_guest:
            logger.info(f"Guest user detected: {context.user_id}")
            return NEEDS_LOGIN_STATUS

        # Step 5: Handle active deployment
        if context.deployment_started and context.deployment_build_id:
            logger.info(
                f"Deployment in progress for user {context.user_id}: "
                f"Build ID {context.deployment_build_id}"
            )
            return DEPLOYING_STATUS_TEMPLATE.format(
                build_id=context.deployment_build_id,
                namespace=context.deployment_namespace,
            )

        # Step 6: Check deployment status
        url = _construct_environment_url(context.user_id)
        deployed = await _check_environment_deployed(url, context.user_id)
        _store_environment_info(tool_context, url, deployed)

        # Step 7: Return appropriate status
        if deployed:
            return DEPLOYED_STATUS_TEMPLATE.format(url=url)
        else:
            return NOT_DEPLOYED_STATUS_TEMPLATE.format(url=url)

    except Exception as e:
        logger.error(f"Error checking environment status: {e}", exc_info=True)
        return ERROR_STATUS_TEMPLATE.format(error=str(e))
