"""Tool for deploying user applications."""

from __future__ import annotations

import httpx
import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from common.config.config import ADK_TEST_MODE
from application.agents.shared.hooks import creates_hook, wrap_response_with_hook
from application.services.deployment.service import get_deployment_service

from ..helpers._deployment_helpers import handle_deployment_success
from ...common.formatters.formatters import (
    format_deployment_started_message,
    format_validation_error,
    format_env_name_prompt_suggestion,
    format_app_name_prompt_suggestion,
)

logger = logging.getLogger(__name__)


def _validate_deployment_inputs(
    env_name: Optional[str],
    app_name: Optional[str],
    cyoda_client_id: str,
    cyoda_client_secret: str,
) -> Optional[str]:
    """Validate deployment input parameters.

    Args:
        env_name: Environment name.
        app_name: Application name.
        cyoda_client_id: Cyoda client ID.
        cyoda_client_secret: Cyoda client secret.

    Returns:
        Error message if validation fails, None otherwise.
    """
    if not env_name:
        return format_validation_error("env_name", format_env_name_prompt_suggestion())

    if not app_name:
        return format_validation_error("app_name", format_app_name_prompt_suggestion())

    if app_name.lower() == "cyoda":
        return (
            "Error: app_name parameter cannot be 'cyoda'. "
            "Please ask the user to choose a different name for their application."
        )

    if not cyoda_client_id or not cyoda_client_id.strip():
        return (
            "Error: cyoda_client_id is required to deploy user applications. "
            "Please ask the user to provide their Cyoda client ID."
        )

    if not cyoda_client_secret or not cyoda_client_secret.strip():
        return (
            "Error: cyoda_client_secret is required to deploy user applications. "
            "Please ask the user to provide their Cyoda client secret."
        )

    return None


def _validate_user_authentication(user_id: str) -> Optional[str]:
    """Validate user authentication status.

    Args:
        user_id: User identifier.

    Returns:
        Error message if user is not authenticated, None otherwise.
    """
    if ADK_TEST_MODE:
        logger.info("ADK_TEST_MODE=true: Skipping authentication check for user application deployment")
        return None

    if user_id.startswith("guest"):
        logger.warning(f"Deployment rejected for guest user: {user_id}")
        return (
            "Error: Deploying user applications is only available to logged-in users. "
            "Please sign up or log in first."
        )

    return None


def _validate_context_state(tool_context: ToolContext) -> Optional[str]:
    """Validate required context state.

    Args:
        tool_context: Tool execution context.

    Returns:
        Error message if context is invalid, None otherwise.
    """
    conversation_id = tool_context.state.get("conversation_id")
    if not conversation_id:
        return "Error: Unable to determine conversation ID. Please try again."

    return None


@creates_hook("background_task")
@creates_hook("cloud_window")
@creates_hook("open_tasks_panel")
async def deploy_user_application(
        tool_context: ToolContext,
        repository_url: str,
        branch_name: str,
        cyoda_client_id: str,
        cyoda_client_secret: str,
        env_name: Optional[str] = None,
        app_name: Optional[str] = None,
        is_public: bool = True,
        installation_id: Optional[str] = None,
) -> str:
    """Deploy a user application to their Cyoda environment.

    Validates inputs, authenticates user, calls deployment service, and creates
    background task for monitoring deployment progress.

    Args:
        tool_context: ADK tool context.
        repository_url: Git repository URL.
        branch_name: Git branch to deploy.
        cyoda_client_id: Cyoda client ID.
        cyoda_client_secret: Cyoda client secret.
        env_name: Environment name (REQUIRED).
        app_name: Application name (REQUIRED).
        is_public: Whether repository is public.
        installation_id: GitHub installation ID.

    Returns:
        Success message with deployment details, or error message.
    """
    try:
        # Validate deployment inputs
        validation_error = _validate_deployment_inputs(
            env_name, app_name, cyoda_client_id, cyoda_client_secret
        )
        if validation_error:
            return validation_error

        # Validate context state
        context_error = _validate_context_state(tool_context)
        if context_error:
            return context_error

        conversation_id = tool_context.state.get("conversation_id")
        user_id = tool_context.state.get("user_id", "guest")
        logger.info(f"User application deployment requested by user_id: {user_id}")

        # Validate user authentication
        auth_error = _validate_user_authentication(user_id)
        if auth_error:
            return auth_error

        # Call deployment service
        deployment_service = get_deployment_service()
        result = await deployment_service.deploy_user_application(
            user_id=user_id,
            conversation_id=conversation_id,
            env_name=env_name,
            app_name=app_name,
            repository_url=repository_url,
            branch_name=branch_name,
            cyoda_client_id=cyoda_client_id,
            cyoda_client_secret=cyoda_client_secret,
            is_public=is_public,
            installation_id=installation_id,
        )

        logger.info(f"User application deployment started: build_id={result.build_id}")

        # Create background task and hooks
        task_id, hook = await handle_deployment_success(
            tool_context=tool_context,
            build_id=result.build_id,
            namespace=result.namespace,
            deployment_type="user_application_deployment",
            task_name=f"Deploy application: {repository_url}",
            task_description=f"Deploying user application from {repository_url}@{branch_name}",
            env_url=None,
            additional_metadata={"repository_url": repository_url, "branch_name": branch_name},
        )

        # Format and return response
        message = format_deployment_started_message(
            build_id=result.build_id,
            repository_url=repository_url,
            branch_name=branch_name,
            user_id=user_id,
            task_id=task_id,
            namespace=result.namespace,
        )

        return wrap_response_with_hook(message, hook) if hook else message

    except httpx.HTTPStatusError as e:
        logger.error(f"Deployment failed with status {e.response.status_code}: {e.response.text}")
        return (
            f"Error: Deployment request failed with status {e.response.status_code}. "
            "Please verify your repository URL and credentials and try again."
        )

    except httpx.HTTPError as e:
        logger.error(f"Network error during deployment: {str(e)}")
        return f"Error: Network error during deployment request: {str(e)}. Please check your connection and try again."

    except ValueError as e:
        logger.error(f"Deployment validation error: {str(e)}")
        return f"Error: Deployment validation error: {str(e)}. Please try again or contact support."

    except Exception as e:
        logger.exception(f"Unexpected error during application deployment: {str(e)}")
        return f"Error: Unexpected error during application deployment: {str(e)}. Please contact support."
