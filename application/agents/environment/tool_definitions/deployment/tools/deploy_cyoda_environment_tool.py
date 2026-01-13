"""Tool for deploying a Cyoda environment."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from application.services.deployment.service import get_deployment_service
from common.config.config import ADK_TEST_MODE

from ...common.formatters.formatters import (
    format_env_name_prompt_suggestion,
    format_environment_deployment_message,
    format_validation_error,
)
from ...common.utils.utils import handle_tool_errors, require_authenticated_user
from ..helpers._conversation_helpers import update_conversation_workflow_cache
from ..helpers._deployment_helpers import handle_deployment_success

logger = logging.getLogger(__name__)

# User validation constants
GUEST_USER_PREFIX = "guest"
GUEST_DEPLOYMENT_ERROR = (
    "Error: Deploying Cyoda environments is only available to logged-in users. "
    "Please sign up or log in first."
)
NO_CONVERSATION_ERROR = "Error: Unable to determine conversation ID. Please try again."

# Task configuration constants
DEPLOYMENT_TASK_TYPE = "environment_deployment"
TASK_NAME_FORMAT = "Deploy Cyoda environment: {namespace}"
TASK_DESCRIPTION_FORMAT = "Deploying Cyoda environment to namespace {namespace}"


class DeploymentContext(BaseModel):
    """Extracted context for deployment operation."""

    user_id: str
    conversation_id: str
    env_name: str
    build_id: Optional[str] = None


class DeploymentInput(BaseModel):
    """Input validation for deployment request."""

    env_name: Optional[str] = None
    build_id: Optional[str] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate deployment input.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.env_name:
            return False, format_validation_error(
                "env_name", format_env_name_prompt_suggestion()
            )
        return True, None


async def _extract_deployment_context(
    tool_context: ToolContext, env_name: Optional[str], build_id: Optional[str]
) -> Tuple[bool, Optional[str], Optional[DeploymentContext]]:
    """Extract and validate deployment context from tool context.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to deploy
        build_id: Optional build ID

    Returns:
        Tuple of (is_valid, error_message, deployment_context)
    """
    # Validate input
    deployment_input = DeploymentInput(env_name=env_name, build_id=build_id)
    is_valid, error_msg = deployment_input.validate()
    if not is_valid:
        return False, error_msg, None

    # Extract context from tool state
    user_id = tool_context.state.get("user_id", "guest")
    conversation_id = tool_context.state.get("conversation_id")

    # Validate user is authenticated (skip if ADK test mode enabled)
    if not ADK_TEST_MODE and user_id.startswith(GUEST_USER_PREFIX):
        logger.warning(f"Deployment rejected for guest user: {user_id}")
        return False, GUEST_DEPLOYMENT_ERROR, None

    if ADK_TEST_MODE:
        logger.info(f"ADK_TEST_MODE=true: Skipping authentication check for deployment")

    # Validate conversation ID
    if not conversation_id:
        return False, NO_CONVERSATION_ERROR, None

    logger.info(f"Environment deployment requested by user_id: {user_id}")

    context = DeploymentContext(
        user_id=user_id,
        conversation_id=conversation_id,
        env_name=env_name,
        build_id=build_id,
    )

    return True, None, context


async def _execute_deployment(
    deployment_context: DeploymentContext,
) -> any:
    """Execute the deployment service call.

    Args:
        deployment_context: Extracted deployment context

    Returns:
        Deployment result from service
    """
    deployment_service = get_deployment_service()
    result = await deployment_service.deploy_cyoda_environment(
        user_id=deployment_context.user_id,
        conversation_id=deployment_context.conversation_id,
        env_name=deployment_context.env_name,
        build_id=deployment_context.build_id,
    )
    return result


async def _handle_post_deployment(
    tool_context: ToolContext, deployment_context: DeploymentContext, result: any
) -> Tuple[str, Optional[str]]:
    """Handle post-deployment tasks (background task, cache update, response formatting).

    Args:
        tool_context: The ADK tool context
        deployment_context: Extracted deployment context
        result: Deployment service result

    Returns:
        Tuple of (message, formatted_response)
    """
    # Step 1: Create background task and hooks
    task_id, hook = await handle_deployment_success(
        tool_context=tool_context,
        build_id=result.build_id,
        namespace=result.namespace,
        deployment_type=DEPLOYMENT_TASK_TYPE,
        task_name=TASK_NAME_FORMAT.format(namespace=result.namespace),
        task_description=TASK_DESCRIPTION_FORMAT.format(namespace=result.namespace),
        env_url=result.env_url,
        additional_metadata={"keyspace": result.keyspace},
    )

    # Step 2: Update conversation workflow cache
    await update_conversation_workflow_cache(
        conversation_id=deployment_context.conversation_id,
        build_id=result.build_id,
        namespace=result.namespace,
    )

    # Step 3: Format response message
    message = format_environment_deployment_message(
        build_id=result.build_id,
        namespace=result.namespace,
        env_url=result.env_url,
        user_id=deployment_context.user_id,
        task_id=task_id,
    )

    return message, hook


@require_authenticated_user
@handle_tool_errors
async def deploy_cyoda_environment(
    tool_context: ToolContext,
    env_name: Optional[str] = None,
    build_id: Optional[str] = None,
) -> str:
    """Deploy a new Cyoda environment for the user.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name (REQUIRED)
        build_id: Optional build ID to associate with deployment

    Returns:
        Success message with deployment details or error message

    Example:
        >>> result = await deploy_cyoda_environment(
        ...     tool_context=context,
        ...     env_name="production",
        ...     build_id="build-123"
        ... )
    """
    # Step 1: Extract and validate deployment context
    is_valid, error_msg, deployment_context = await _extract_deployment_context(
        tool_context, env_name, build_id
    )
    if not is_valid:
        return error_msg

    # Step 2: Execute deployment
    result = await _execute_deployment(deployment_context)

    # Step 3: Handle post-deployment tasks
    message, hook = await _handle_post_deployment(
        tool_context, deployment_context, result
    )

    # Step 4: Return response (hook functionality removed)
    return message
