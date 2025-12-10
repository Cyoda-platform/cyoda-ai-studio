"""Tools for the Environment Management agent."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from application.entity.conversation import Conversation
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def _get_cloud_manager_auth_token() -> str:
    """Get authentication token for cloud manager API.

    Returns:
        The access token for cloud manager API

    Raises:
        Exception: If authentication fails or credentials are not configured
    """
    import base64
    import httpx

    # Get cloud manager access token
    cloud_manager_api_key_encoded = os.getenv("CLOUD_MANAGER_API_KEY")
    cloud_manager_api_secret_encoded = os.getenv("CLOUD_MANAGER_API_SECRET")

    if not cloud_manager_api_key_encoded or not cloud_manager_api_secret_encoded:
        raise Exception("Cloud manager credentials not configured")

    # Decode base64 credentials
    cloud_manager_api_key = base64.b64decode(
        cloud_manager_api_key_encoded
    ).decode("utf-8")
    cloud_manager_api_secret = base64.b64decode(
        cloud_manager_api_secret_encoded
    ).decode("utf-8")

    # Determine protocol
    cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
    protocol = "http" if cloud_manager_host and "localhost" in cloud_manager_host else "https"

    # Authenticate with cloud manager
    auth_url = f"{protocol}://cloud-manager-cyoda.kube3.cyoda.org/api/auth/login"
    auth_payload = {
        "username": cloud_manager_api_key,
        "password": cloud_manager_api_secret,
    }
    auth_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        auth_response = await client.post(
            auth_url, json=auth_payload, headers=auth_headers
        )
        auth_response.raise_for_status()
        auth_data = auth_response.json()
        access_token = auth_data.get("token")

        if not access_token:
            raise Exception("Failed to authenticate with cloud manager")

        return access_token


async def _handle_deployment_success(
        tool_context: ToolContext,
        build_id: str,
        namespace: str,
        deployment_type: str,
        task_name: str,
        task_description: str,
        env_url: Optional[str] = None,
        additional_metadata: Optional[dict[str, Any]] = None,
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """Handle common post-deployment logic: create BackgroundTask, start monitoring, create hooks.

    Args:
        tool_context: The ADK tool context
        build_id: The deployment build ID
        namespace: The deployment namespace
        deployment_type: Type of deployment (e.g., "environment_deployment", "user_application_deployment")
        task_name: Name for the background task
        task_description: Description for the background task
        env_url: Optional environment URL
        additional_metadata: Optional additional metadata to include in task

    Returns:
        Tuple of (task_id, hook_dict) where hook_dict is the combined hook to be set in tool_context
    """
    task_id = None
    hook = None
    conversation_id = tool_context.state.get("conversation_id")
    user_id = tool_context.state.get("user_id", "guest")

    # Construct environment URL if not provided
    if not env_url and namespace:
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        env_url = f"https://{namespace}.{client_host}"

    # Prepare metadata
    metadata = {
        "build_id": build_id,
        "namespace": namespace,
        "env_url": env_url,
    }
    if additional_metadata:
        metadata.update(additional_metadata)

    # Create BackgroundTask entity to track deployment progress
    if conversation_id:
        try:
            from services.services import get_task_service

            task_service = get_task_service()

            logger.info(f"🔧 Creating BackgroundTask with user_id={user_id}, conversation_id={conversation_id}")

            # Create background task
            background_task = await task_service.create_task(
                user_id=user_id,
                task_type=deployment_type,
                name=task_name,
                description=task_description,
                conversation_id=conversation_id,
                build_id=build_id,
                namespace=namespace,
                env_url=env_url,
            )

            task_id = background_task.technical_id
            logger.info(f"✅ Created BackgroundTask {task_id} for {deployment_type}")

            # Update task to in_progress status
            await task_service.update_task_status(
                task_id=task_id,
                status="in_progress",
                message=f"Deployment started: {namespace}",
                progress=10,
                metadata=metadata,
            )
            logger.info(f"✅ Updated BackgroundTask {task_id} to in_progress")

            # Store task_id in context for monitoring
            tool_context.state["deployment_task_id"] = task_id

            # Add task to conversation's background_task_ids
            from application.agents.shared.repository_tools import _add_task_to_conversation

            logger.info(f"🔧 Adding task {task_id} to conversation {conversation_id}")
            await _add_task_to_conversation(conversation_id, task_id)
            logger.info(f"✅ Added task {task_id} to conversation {conversation_id}")

        except Exception as e:
            logger.error(f"❌ Failed to create BackgroundTask for {deployment_type}: {e}", exc_info=True)
            logger.error(f"❌ user_id={user_id}, conversation_id={conversation_id}, namespace={namespace}")
            # Continue anyway - task tracking is not critical for deployment execution
    else:
        logger.warning(f"⚠️ No conversation_id in tool_context.state - cannot create BackgroundTask")

    # Store deployment info in session state
    tool_context.state["build_id"] = build_id
    tool_context.state["build_namespace"] = namespace
    tool_context.state["deployment_type"] = deployment_type
    tool_context.state["deployment_started"] = True
    tool_context.state["deployment_build_id"] = build_id
    tool_context.state["deployment_namespace"] = namespace

    # Start monitoring deployment progress in background
    if task_id:
        import asyncio
        asyncio.create_task(
            _monitor_deployment_progress(
                build_id=build_id,
                task_id=task_id,
                tool_context=tool_context,
            )
        )
        logger.info(f"🔍 Started monitoring task for deployment {build_id}")

    # Create hooks
    if conversation_id and task_id:
        from application.agents.shared.hook_utils import (
            create_cloud_window_hook,
            create_background_task_hook,
            create_combined_hook,
        )

        # Create background task hook
        task_hook = create_background_task_hook(
            task_id=task_id,
            task_type=deployment_type,
            task_name=task_name,
            task_description=task_description,
            conversation_id=conversation_id,
            metadata=metadata,
        )

        # If we have env_url, combine with cloud window hook
        if env_url:
            cloud_hook = create_cloud_window_hook(
                conversation_id=conversation_id,
                environment_url=env_url,
                environment_status="deploying",
                message=f"Deployment started! Track progress in the Cloud panel.",
            )
            # Combine both hooks
            hook = create_combined_hook(
                code_changes_hook=cloud_hook,  # Reuse code_changes slot for cloud hook
                background_task_hook=task_hook,
            )
        else:
            # Just background task hook
            hook = task_hook

        # Store hook in context
        tool_context.state["last_tool_hook"] = hook

    return task_id, hook


async def check_environment_exists(tool_context: ToolContext, env_name: Optional[str] = None) -> str:
    """Check if a Cyoda environment exists for the current user.

    Attempts to access the user's environment URL to determine if it's deployed.
    This is useful for determining whether to issue credentials or deploy a new environment.

    Creates a cloud_window hook to open the Cloud/Environments panel in the UI.

    IMPORTANT: You MUST ask the user for env_name before calling this function. DO NOT assume or infer the environment name.
    The user might have multiple environments (dev, staging, prod, etc.), so you must explicitly ask them which environment to check.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to check. REQUIRED - must be provided by the user.
                  If not provided, this function will return an error asking you to prompt the user.
                  Example prompt: "Which environment would you like to check? For example: 'dev', 'prod', 'staging', etc."

    Returns:
        JSON string with environment status and hook:
        - {"exists": true, "url": "https://...", "message": "...", "hook": {...}} if environment exists
        - {"exists": false, "url": "https://...", "message": "...", "hook": {...}} if environment doesn't exist
    """
    try:
        from common.exception.exceptions import InvalidTokenException
        from common.utils.utils import send_get_request
        from application.agents.shared.hook_utils import (
            create_cloud_window_hook,
            wrap_response_with_hook,
        )

        # Get user ID and conversation ID from context
        user_id = tool_context.state.get("user_id", "guest")
        conversation_id = tool_context.state.get("conversation_id")

        if not env_name:
            return "ERROR: env_name parameter is required but was not provided. You MUST ask the user which environment to check before calling this function. Ask them: 'Which environment would you like to check? For example: dev, prod, staging, etc.' DO NOT assume or infer the environment name."

        if user_id.startswith("guest"):
            result = {
                "exists": False,
                "url": None,
                "message": "User is not logged in. Please sign up or log in first."
            }
            return json.dumps(result)

        # Construct environment URL using the same pattern as deploy functions
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        url = f"https://{namespace}.{client_host}"

        try:
            # Try to access the environment API to check if it's deployed
            await send_get_request(api_url=url, path="api/v1", token="guest_token")
            # If we get here without exception, something unexpected happened
            result = {
                "exists": False,
                "url": url,
                "message": f"Environment status unclear for {url}"
            }

            # Create hook to open Cloud window
            if conversation_id:
                hook = create_cloud_window_hook(
                    conversation_id=conversation_id,
                    environment_url=url,
                    environment_status="unknown",
                    message="Check your environment status in the Cloud panel.",
                )
                tool_context.state["last_tool_hook"] = hook
                return wrap_response_with_hook(result["message"], hook)

            return json.dumps(result)

        except InvalidTokenException:
            # InvalidTokenException means the environment exists and is responding
            logger.info(f"✅ Environment exists for user {user_id}: {url}")
            result = {
                "exists": True,
                "url": url,
                "message": f"Your Cyoda environment is deployed and accessible at {url}"
            }

            # Create hook to open Cloud window
            if conversation_id:
                hook = create_cloud_window_hook(
                    conversation_id=conversation_id,
                    environment_url=url,
                    environment_status="deployed",
                    message="Your environment is ready! View details in the Cloud panel.",
                )
                tool_context.state["last_tool_hook"] = hook
                return wrap_response_with_hook(result["message"], hook)

            return json.dumps(result)

        except Exception as e:
            # Any other exception means environment is not deployed
            logger.info(f"Environment not deployed for user {user_id}: {e}")
            result = {
                "exists": False,
                "url": url,
                "message": f"No Cyoda environment found at {url}. You can deploy one using deploy_cyoda_environment()."
            }

            # Create hook to open Cloud window
            if conversation_id:
                hook = create_cloud_window_hook(
                    conversation_id=conversation_id,
                    environment_url=url,
                    environment_status="not_deployed",
                    message="No environment found. Deploy one from the Cloud panel.",
                )
                tool_context.state["last_tool_hook"] = hook
                return wrap_response_with_hook(result["message"], hook)

            return json.dumps(result)

    except Exception as e:
        error_msg = f"Error checking environment: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({
            "exists": False,
            "url": None,
            "message": error_msg
        })


def _get_keyspace(user_name: str):
    keyspace = re.sub(r"[^a-z0-9_]", "_", user_name.lower())
    return keyspace


def _get_namespace(user_name: str):
    namespace = re.sub(r"[^a-z0-9-]", "-", user_name.lower())
    # Enforce max 10 characters - truncate if longer
    return namespace


async def deploy_cyoda_environment(
        tool_context: ToolContext, env_name: Optional[str] = None, build_id: Optional[str] = None,
) -> str:
    """Deploy a new Cyoda environment for the user.

    Provisions a complete Cyoda environment including infrastructure,
    databases, and services. Creates a BackgroundTask entity to track deployment progress.

    IMPORTANT: You MUST ask the user for env_name before calling this function. DO NOT assume or infer the environment name.
    The user might have multiple environments (dev, staging, prod, etc.), so you must explicitly ask them which environment name to use.

    Args:
      tool_context: The ADK tool context
      env_name: Environment name/namespace to use for deployment. REQUIRED - must be provided by the user.
                If not provided, this function will return an error asking you to prompt the user.
                Example prompt: "What environment name would you like to use? For example: 'dev', 'prod', 'staging', etc." Max 10 characters. Other characters will be concatenated
      build_id: Optional build ID to associate with this deployment (e.g., from application build)

    Returns:
      Success message with build ID, task ID, and environment URL, or error message
    """
    try:
        import base64
        import uuid

        import httpx

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return "Error: CLOUD_MANAGER_HOST environment variable not configured. Please contact your administrator."

        # Check user authentication
        user_id = tool_context.state.get("user_id", "guest")
        logger.info(f"Environment deployment requested by user_id: {user_id}")

        if not env_name:
            return "ERROR: env_name parameter is required but was not provided. You MUST ask the user for the environment name before calling this function. Ask them: 'What environment name would you like to use? For example: dev, prod, staging, etc.' DO NOT assume or infer the environment name."
        env_name = env_name[:10]  # Truncate to 10 characters
        if user_id.startswith("guest"):
            logger.warning(f"Deployment rejected for guest user: {user_id}")
            return "Sorry, deploying Cyoda environments is only available to logged-in users. Please sign up or log in first."

        # Construct deployment URL
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        deploy_url = os.getenv(
            "DEPLOY_CYODA_ENV", f"{protocol}://{cloud_manager_host}/deploy/cyoda-env"
        )

        # Get chat_id from session state (conversation_id)
        chat_id = tool_context.state.get("conversation_id")
        if not chat_id:
            return "Error: Unable to determine conversation ID. Please try again."

        # Prepare deployment request with correct API format
        payload = {"user_name": user_id, "chat_id": chat_id}

        # Add optional parameters if provided
        if build_id:
            payload["build_id"] = build_id
            logger.info(f"Including build_id in deployment request: {build_id}")

        payload["user_defined_namespace"] = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        payload["user_defined_keyspace"] = f"c_{_get_keyspace(user_id)}_{_get_keyspace(env_name)}"

        logger.info(
            f"Deploying Cyoda environment for user: {user_id}, chat_id: {chat_id}"
        )

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return f"Error: Failed to authenticate with cloud manager: {str(e)}"

        # Make deployment request with authentication
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes for environment check
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.post(deploy_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            deployment_build_id = data.get("build_id")
            namespace = data.get("build_namespace")

            if not deployment_build_id or not namespace:
                return "Error: Deployment request succeeded but missing build information. Please try again."

            logger.info(
                f"Environment deployment started: build_id={deployment_build_id}, namespace={namespace}"
            )

            # Handle deployment success: create BackgroundTask, start monitoring, create hooks
            task_id, hook = await _handle_deployment_success(
                tool_context=tool_context,
                build_id=deployment_build_id,
                namespace=namespace,
                deployment_type="environment_deployment",
                task_name=f"Deploy Cyoda environment: {namespace}",
                task_description=f"Deploying Cyoda environment to namespace {namespace}",
                env_url=None,  # Will be constructed from namespace
                additional_metadata=None,
            )

            # Also store build_id in Conversation's workflow_cache for persistence
            conversation_id = tool_context.state.get("conversation_id")
            if conversation_id:
                try:
                    from services.services import get_entity_service
                    from application.entity.conversation.version_1.conversation import Conversation

                    entity_service = get_entity_service()
                    conversation_response = await entity_service.get_by_id(
                        entity_id=conversation_id,
                        entity_class=Conversation.ENTITY_NAME,
                        entity_version=str(Conversation.ENTITY_VERSION),
                    )

                    if conversation_response and conversation_response.data:
                        conversation_data = conversation_response.data if isinstance(conversation_response.data,
                                                                                     dict) else conversation_response.data.model_dump(
                            by_alias=False)
                        conversation = Conversation(**conversation_data)

                        # Update workflow_cache with build_id
                        conversation.workflow_cache["build_id"] = deployment_build_id
                        conversation.workflow_cache["namespace"] = namespace
                        logger.info(
                            f"📋 Updated workflow_cache with build_id={deployment_build_id}, namespace={namespace}")

                        # Update conversation
                        entity_dict = conversation.model_dump(by_alias=False)
                        await entity_service.update(
                            entity_id=conversation_id,
                            entity=entity_dict,
                            entity_class=Conversation.ENTITY_NAME,
                            entity_version=str(Conversation.ENTITY_VERSION),
                        )
                        logger.info(
                            f"✅ Successfully updated conversation {conversation_id} with build_id in workflow_cache")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update conversation workflow_cache with build_id: {e}")
                    # Continue anyway - this is not critical for deployment

            # Return success with task_id for UI tracking
            result = f"SUCCESS: Environment deployment started (Build ID: {deployment_build_id}, Namespace: {namespace}"
            if task_id:
                result += f", Task ID: {task_id}"
            result += ")"

            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"Deployment request failed with status {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return f"Error: {error_msg}. Please try again or contact support."
    except httpx.HTTPError as e:
        error_msg = f"Network error during deployment request: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}. Please check your connection and try again."
    except Exception as e:
        error_msg = f"Unexpected error during environment deployment: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}. Please contact support."


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

    Builds and deploys the user's application code to their provisioned
    Cyoda environment. Supports both Python and Java applications.

    IMPORTANT: You MUST ask the user for both env_name and app_name before calling this function. DO NOT assume or infer these values.
    The user might have multiple environments and applications, so you must explicitly ask them.

    Args:
      tool_context: The ADK tool context
      repository_url: Git repository URL containing the application code
      branch_name: Git branch to deploy (e.g., "main", "develop", or branch UUID)
      cyoda_client_id: Cyoda client ID for authentication
      cyoda_client_secret: Cyoda client secret for authentication
      env_name: Environment name to deploy to. REQUIRED - must be provided by the user.
                If not provided, this function will return an error asking you to prompt the user.
                Example prompt: "What environment name would you like to deploy to? For example: 'dev', 'prod', 'staging', etc."
      app_name: Application name for this deployment. REQUIRED - must be provided by the user.
                If not provided, this function will return an error asking you to prompt the user.
                Example prompt: "What would you like to name this application? For example: 'my-app', 'payment-api', 'dashboard-v2', etc. Max 10 characters. Other characters will be concatenated."
      is_public: Whether the repository is public (default: True)
      installation_id: GitHub installation ID for public repos (optional)

    Returns:
      Success message with deployment details, or error message
    """
    try:
        import httpx

        if not env_name:
            return "ERROR: env_name parameter is required but was not provided. You MUST ask the user for the environment name before calling this function. Ask them: 'What environment would you like to deploy to? For example: dev, prod, staging, etc.' DO NOT assume or infer the environment name."

        if not app_name:
            return "ERROR: app_name parameter is required but was not provided. You MUST ask the user for the application name before calling this function. Ask them: 'What would you like to name this application? For example: my-app, payment-api, dashboard-v2, etc.' DO NOT assume or infer the application name."

        if app_name.lower() == "cyoda":
            return "ERROR: app_name parameter cannot be 'cyoda'. Please ask the user to choose a different name for their application."
        app_name = app_name[:10]  # Truncate to 10 characters
        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return "Error: CLOUD_MANAGER_HOST environment variable not configured. Please contact your administrator."

        # Construct deployment URL
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        deploy_url = os.getenv(
            "DEPLOY_USER_APP", f"{protocol}://{cloud_manager_host}/deploy/user-app"
        )

        # Get chat_id from session state (conversation_id)
        chat_id = tool_context.state.get("conversation_id")
        if not chat_id:
            return "Error: Unable to determine conversation ID. Please try again."
        user_id = tool_context.state.get("user_id", "guest")
        logger.info(f"Environment deployment requested by user_id: {user_id}")
        if user_id.startswith("guest"):
            logger.warning(f"Deployment rejected for guest user: {user_id}")
            return "Sorry, deploying Cyoda environments is only available to logged-in users. Please sign up or log in first."

# Prepare deployment payload matching the working example format
        cyoda_namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        app_namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"


        payload = {
            "branch_name": branch_name,
            "chat_id": chat_id,
            "cyoda_client_id": cyoda_client_id,
            "cyoda_client_secret": cyoda_client_secret,
            "is_public": str(is_public).lower(),
            "repository_url": repository_url,
            "user_name": user_id,
            "app_namespace": app_namespace,
            "cyoda_namespace": cyoda_namespace,
        }

        # Add installation ID if provided (for public repos)
        if installation_id:
            payload["installation_id"] = installation_id
        elif is_public:
            # Try to get from environment if not provided
            env_installation_id = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")
            if env_installation_id:
                payload["installation_id"] = env_installation_id

        logger.info(
            f"Deploying user application from {repository_url}@{branch_name} for user {user_id}"
        )

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return f"Error: Failed to authenticate with cloud manager: {str(e)}"

        # Make deployment request with authentication
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes for deployment
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.post(deploy_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            build_id = data.get("build_id")
            namespace = data.get("build_namespace") or data.get("namespace")

            if not build_id:
                return "Error: Deployment request succeeded but missing build ID. Please try again."

            logger.info(f"User application deployment started: build_id={build_id}")

            # Handle deployment success: create BackgroundTask, start monitoring, create hooks
            task_id, hook = await _handle_deployment_success(
                tool_context=tool_context,
                build_id=build_id,
                namespace=namespace,
                deployment_type="user_application_deployment",
                task_name=f"Deploy application: {repository_url}",
                task_description=f"Deploying user application from {repository_url}@{branch_name}",
                env_url=None,  # Will be constructed from namespace
                additional_metadata={
                    "repository_url": repository_url,
                    "branch_name": branch_name,
                },
            )

            # Return success with task_id for UI tracking
            result = f"✓ Application deployment started successfully!\n\n**Build ID:** {build_id}\n**Repository:** {repository_url}\n**Branch:** {branch_name}\n**User:** {user_id}"
            if task_id:
                result += f"\n**Task ID:** {task_id}"
            if namespace:
                result += f"\n**Namespace:** {namespace}"

            result += "\n\nYour application is being built and deployed. This typically takes 3-5 minutes.\n\nI'll keep you updated on the progress!"

            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"Deployment request failed with status {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return f"Error: {error_msg}. Please verify your repository URL and credentials and try again."
    except httpx.HTTPError as e:
        error_msg = f"Network error during deployment request: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}. Please check your connection and try again."
    except Exception as e:
        error_msg = f"Unexpected error during application deployment: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}. Please contact support."


async def get_deployment_status(
        tool_context: ToolContext, build_id: str, for_monitoring: bool = False
) -> str:
    """Check the deployment status for a specific build.

    Queries the cloud manager to get the current state and status of
    a deployment or build operation.

    Args:
      tool_context: The ADK tool context
      build_id: The build identifier to check status for
      for_monitoring: If True, returns structured data for monitoring loop

    Returns:
      Formatted deployment status information, or error message
    """
    try:
        import httpx

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return "Error: CLOUD_MANAGER_HOST environment variable not configured."

        # Construct status URL
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        status_url = os.getenv(
            "DEPLOY_CYODA_ENV_STATUS",
            f"{protocol}://{cloud_manager_host}/deploy/cyoda-env/status",
        )

        logger.info(f"Checking deployment status for build_id: {build_id}")

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return f"Error: Failed to authenticate with cloud manager: {str(e)}"

        # Make status request with authentication
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(f"{status_url}?build_id={build_id}", headers=headers)
            response.raise_for_status()

            data = response.json()
            state = data.get("state", "UNKNOWN")
            status = data.get("status", "UNKNOWN")
            message = data.get("message", "")

            # Store status in session state for monitoring
            tool_context.state[f"deployment_status_{build_id}"] = {
                "state": state,
                "status": status,
                "message": message,
            }

            # For monitoring loop, return structured data
            if for_monitoring:
                # Treat UNKNOWN status as failure regardless of state
                is_complete = state.upper() in ["COMPLETE", "SUCCESS", "FINISHED"] and status.upper() != "UNKNOWN"
                is_failed = state.upper() in ["FAILED", "ERROR", "UNKNOWN"] or status.upper() == "UNKNOWN"
                return f"STATUS:{state}|{status}|{'DONE' if (is_complete or is_failed) else 'CONTINUE'}"

            # Format status message based on state
            status_emoji = {
                "PENDING": "⏳",
                "RUNNING": "🔄",
                "COMPLETE": "✅",
                "SUCCESS": "✅",
                "FINISHED": "✅",
                "FAILED": "❌",
                "ERROR": "❌",
                "UNKNOWN": "❌",
            }.get(state.upper(), "📊")

            result = f"""{status_emoji} **Deployment Status for Build {build_id}**

**State:** {state}
**Status:** {status}"""

            if message:
                result += f"\n**Message:** {message}"

            # Add helpful next steps based on state and status
            if status.upper() == "UNKNOWN":
                result += "\n\n⚠️ Deployment failed: status is UNKNOWN. You can check the build logs for more details."
            elif state.upper() in ["COMPLETE", "SUCCESS", "FINISHED"]:
                result += "\n\n✓ Deployment completed successfully! Your environment is ready to use."
            elif state.upper() in ["FAILED", "ERROR", "UNKNOWN"]:
                result += "\n\n⚠️ Deployment failed. You can check the build logs for more details."
            elif state.upper() in ["PENDING", "RUNNING"]:
                result += "\n\n⏳ Deployment is still in progress. I'll keep monitoring for you."

            logger.info(f"Deployment status for {build_id}: {state}/{status}")
            return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: Build ID '{build_id}' not found. Please verify the build ID and try again."
        error_msg = f"Status request failed with status {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return f"Error: {error_msg}"
    except httpx.HTTPError as e:
        error_msg = f"Network error checking deployment status: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error checking deployment status: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}"


async def get_build_logs(build_id: str, max_lines: int = 100) -> str:
    """Retrieve build logs for debugging deployment issues.

    Fetches the build logs from the cloud manager to help diagnose
    deployment failures or issues.

    Args:
      build_id: The build identifier to get logs for
      max_lines: Maximum number of log lines to retrieve (default: 100)

    Returns:
      Build logs as formatted text, or error message
    """
    try:
        import httpx

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return "Error: CLOUD_MANAGER_HOST environment variable not configured."

        # Construct logs URL
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        logs_url = os.getenv(
            "BUILD_LOGS_URL", f"{protocol}://{cloud_manager_host}/build/logs"
        )

        logger.info(f"Retrieving build logs for build_id: {build_id}")

        # Make logs request
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{logs_url}?build_id={build_id}&max_lines={max_lines}"
            )
            response.raise_for_status()

            data = response.json()
            logs = data.get("logs", "")

            if not logs:
                return f"No logs available for build {build_id}. The build may not have started yet."

            # Format logs for display
            result = f"""📋 **Build Logs for {build_id}**

```
{logs}
```

Showing last {max_lines} lines. For complete logs, check the cloud manager dashboard."""

            logger.info(f"Retrieved {len(logs)} characters of logs for {build_id}")
            return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: Build ID '{build_id}' not found or logs not available yet."
        error_msg = f"Logs request failed with status {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return f"Error: {error_msg}"
    except httpx.HTTPError as e:
        error_msg = f"Network error retrieving build logs: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error retrieving build logs: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}"


async def ui_function_issue_technical_user(tool_context: ToolContext, env_name: Optional[str] = None) -> str:
    """Issue M2M (machine-to-machine) technical user credentials.

    This function stores a UI function call instruction in the tool context
    that tells the frontend to make an API call to issue technical user credentials
    (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication.

    The UI function JSON will be added to the conversation by the agent framework
    after the agent completes its response, preventing race conditions.

    Use this tool when the user asks for credentials or needs to authenticate
    their application with the Cyoda environment.

    IMPORTANT: You MUST ask the user for env_name before calling this function. DO NOT assume or infer the environment name.
    The user might have multiple environments (dev, staging, prod, etc.), so you must explicitly ask them which environment needs credentials.

    Args:
        tool_context: The ADK tool context (auto-injected)
        env_name: Environment name to issue credentials for. REQUIRED - must be provided by the user.
                  If not provided, this function will return an error asking you to prompt the user.
                  Example prompt: "Which environment would you like to issue credentials for? For example: 'dev', 'prod', 'staging', etc."

    Returns:
        Success message confirming credential issuance was initiated
    """
    try:
        logger.info(f"🔧 ui_function_issue_technical_user called with env_name={env_name}")

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        logger.info(f"🔧 user_id from context: {user_id}")

        if not env_name:
            logger.warning("⚠️ env_name not provided to ui_function_issue_technical_user")
            return "ERROR: env_name parameter is required but was not provided. You MUST ask the user which environment to issue credentials for before calling this function. Ask them: 'Which environment would you like to issue credentials for? For example: dev, prod, staging, etc.' DO NOT assume or infer the environment name."

        if user_id.startswith("guest"):
            logger.warning(f"⚠️ Guest user attempted to issue credentials: {user_id}")
            return "Sorry, issuing credentials is only available to logged-in users. Please sign up or log in first."

        # Construct environment URL using the same pattern as other functions
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        env_url = f"{namespace}.{client_host}"
        logger.info(f"🔧 Constructed env_url: {env_url}")

        # Create UI function parameters with environment URL
        ui_params = {
            "type": "ui_function",
            "function": "ui_function_issue_technical_user",
            "method": "POST",
            "path": "/api/clients",
            "response_format": "json",
            "env_url": env_url,
        }

        logger.info(f"🔧 Storing UI function in tool context for environment {env_url}: {json.dumps(ui_params)}")

        # Store UI function in tool context so the agent framework can add it to conversation
        # This prevents race conditions where both the tool and route handler update the conversation
        if "ui_functions" not in tool_context.state:
            logger.info("🔧 Initializing ui_functions list in tool_context.state")
            tool_context.state["ui_functions"] = []
        tool_context.state["ui_functions"].append(ui_params)

        logger.info(f"✅ UI function stored in context for {env_url}. Total ui_functions in state: {len(tool_context.state['ui_functions'])}")

        success_msg = f"✅ Credential issuance initiated for environment: {env_url}\n\nThe UI will create your M2M technical user credentials (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication with this environment."
        logger.info(f"🔧 Returning success message: {success_msg[:100]}...")
        return success_msg

    except Exception as e:
        error_msg = f"Error issuing technical user: {str(e)}"
        logger.exception(error_msg)
        return error_msg


async def _monitor_deployment_progress(
        build_id: str,
        task_id: str,
        tool_context: ToolContext,
        check_interval: int = 30,
        max_checks: int = 40,
) -> None:
    """
    Monitor environment deployment progress and update BackgroundTask entity.

    Polls the cloud manager API every 30 seconds to check deployment status
    and updates the BackgroundTask entity with progress.

    Args:
        build_id: Cloud manager build ID
        task_id: BackgroundTask entity technical ID
        tool_context: Tool context for accessing deployment status API
        check_interval: Seconds between status checks (default: 30)
        max_checks: Maximum number of checks before giving up (default: 40 = 20 minutes)
    """
    import asyncio

    logger.info(f"🔍 Starting deployment monitoring for build_id={build_id}, task_id={task_id}")

    try:
        from services.services import get_task_service
        task_service = get_task_service()

        # Get task to retrieve env_url and namespace
        task = await task_service.get_task(task_id)
        env_url = task.env_url if task else None
        namespace = task.namespace if task else None

        for check_num in range(max_checks):
            await asyncio.sleep(check_interval)

            try:
                # Check deployment status
                status_result = await get_deployment_status(
                    tool_context=tool_context,
                    build_id=build_id,
                    for_monitoring=True,
                )

                # Parse status result (format: "STATUS:state|status|DONE/CONTINUE")
                if status_result.startswith("STATUS:"):
                    parts = status_result.replace("STATUS:", "").split("|")
                    if len(parts) >= 3:
                        state = parts[0]
                        status = parts[1]
                        done_flag = parts[2]

                        # Calculate progress (0-95% during deployment, 100% when complete)
                        if done_flag == "DONE":
                            progress = 100
                        else:
                            # Linear progress from 10% to 95% over max_checks
                            progress = min(95, 10 + int((check_num / max_checks) * 85))

                        # Update BackgroundTask
                        # Check if status is UNKNOWN - treat as failure regardless of state
                        if status.upper() == "UNKNOWN":
                            await task_service.update_task_status(
                                task_id=task_id,
                                status="failed",
                                message=f"Environment deployment failed: status is UNKNOWN (state: {state})",
                                progress=0,
                                error=f"Deployment status is UNKNOWN (state: {state})",
                                metadata={
                                    "build_id": build_id,
                                    "namespace": namespace,
                                    "env_url": env_url,
                                    "state": state,
                                },
                            )
                            logger.error(f"❌ Deployment {build_id} failed: status UNKNOWN (state: {state})")
                            return
                        elif state.upper() in ["COMPLETE", "SUCCESS", "FINISHED"]:
                            await task_service.update_task_status(
                                task_id=task_id,
                                status="completed",
                                message=f"Environment deployment completed: {status}",
                                progress=100,
                                metadata={
                                    "build_id": build_id,
                                    "namespace": namespace,
                                    "env_url": env_url,
                                },
                            )
                            logger.info(f"✅ Deployment {build_id} completed successfully")
                            return
                        elif state.upper() in ["FAILED", "ERROR", "UNKNOWN"]:
                            await task_service.update_task_status(
                                task_id=task_id,
                                status="failed",
                                message=f"Environment deployment failed: {status}",
                                progress=0,
                                error=status,
                                metadata={
                                    "build_id": build_id,
                                    "namespace": namespace,
                                    "env_url": env_url,
                                },
                            )
                            logger.error(f"❌ Deployment {build_id} failed: {status}")
                            return
                        else:
                            # Still in progress
                            await task_service.add_progress_update(
                                task_id=task_id,
                                message=f"Deployment {state}: {status}",
                                progress=progress,
                                metadata={
                                    "build_id": build_id,
                                    "namespace": namespace,
                                    "env_url": env_url,
                                    "state": state,
                                    "check_num": check_num + 1,
                                },
                            )
                            logger.info(f"📊 Deployment {build_id} progress: {progress}% ({state})")

            except Exception as e:
                logger.warning(f"⚠️ Failed to check deployment status (attempt {check_num + 1}): {e}")
                # Continue monitoring even if one check fails

        # Max checks reached without completion
        await task_service.update_task_status(
            task_id=task_id,
            status="failed",
            message=f"Deployment monitoring timeout after {max_checks * check_interval} seconds",
            progress=0,
            error="Monitoring timeout - deployment may still be in progress",
        )
        logger.warning(f"⏰ Deployment monitoring timeout for {build_id}")

    except Exception as e:
        logger.error(f"❌ Error in deployment monitoring: {e}", exc_info=True)


async def show_deployment_options(
        question: str,
        options: list[dict[str, str]],
        tool_context: Optional[ToolContext] = None,
) -> str:
    """Display interactive deployment options to the user.

    This tool allows the LLM to dynamically present options based on the situation.
    The user's selection will be sent back as a message that the agent can parse.

    Args:
        question: The question to display to the user
        options: List of option dictionaries, each with:
            - value: The value to return when selected (required)
            - label: Display text for the option (required)
            - description: Optional description text (optional)
        tool_context: The ADK tool context

    Returns:
        Message with hook for displaying options

    Example:
        result = show_deployment_options(
            question="What would you like to do?",
            options=[
                {
                    "value": "deploy_app",
                    "label": "🚀 Deploy Application",
                    "description": "Deploy your application to the environment"
                },
                {
                    "value": "issue_credentials",
                    "label": "🔐 Issue Technical Credentials",
                    "description": "Get M2M credentials for API access"
                }
            ]
        )
    """
    if not tool_context:
        return "ERROR: Tool context not available. This function must be called within a conversation context."

    # Validate options
    if not options or len(options) == 0:
        return "ERROR: At least one option must be provided."

    for option in options:
        if "value" not in option or "label" not in option:
            return "ERROR: Each option must have 'value' and 'label' fields."

    from application.agents.shared.hook_utils import (
        create_option_selection_hook,
        wrap_response_with_hook,
    )

    # Get conversation ID from context
    conversation_id = tool_context.state.get("conversation_id", "")

    # Create the hook
    hook = create_option_selection_hook(
        conversation_id=conversation_id,
        question=question,
        options=options,
        selection_type="single",
    )

    # Store hook in context for SSE streaming
    tool_context.state["last_tool_hook"] = hook

    # Return message with hook
    message = f"{question}\n\nPlease select your choice using the options below."

    return wrap_response_with_hook(message, hook)


# ==================== K8s Management Operations ====================


async def list_environments(tool_context: ToolContext) -> str:
    """List all environments (namespaces) for the current user.

    Retrieves all namespaces from the cluster and filters them to show only
    those belonging to the current user. Each user can have multiple environments
    (dev, staging, prod, etc.).

    Args:
        tool_context: The ADK tool context

    Returns:
        JSON string with list of environments and their details, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            all_namespaces = data.get("namespaces", [])

            # Filter namespaces for this user (format: client-{user}-{env})
            user_namespace_prefix = f"client-{_get_namespace(user_id)}-"
            user_environments = []

            for ns in all_namespaces:
                ns_name = ns.get("name", "")
                if ns_name.startswith(user_namespace_prefix):
                    # Extract environment name
                    env_name = ns_name.replace(user_namespace_prefix, "")
                    # Skip app namespaces (they contain "-app-")
                    if "-app-" not in env_name:
                        user_environments.append({
                            "name": env_name,
                            "namespace": ns_name,
                            "status": ns.get("status", "Unknown"),
                            "created_at": ns.get("created_at"),
                        })

            result = {
                "environments": user_environments,
                "count": len(user_environments),
            }

            logger.info(f"Found {len(user_environments)} environments for user {user_id}")
            return json.dumps(result)

    except httpx.HTTPStatusError as e:
        error_msg = f"Failed to list namespaces: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error listing environments: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def describe_environment(tool_context: ToolContext, env_name: str) -> str:
    """Describe a Cyoda environment by listing all platform deployments in it.

    This shows the Cyoda platform services running in the environment namespace
    (client-{user}-{env}), NOT user applications which run in separate namespaces.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to describe

    Returns:
        JSON string with list of Cyoda platform deployments and their details, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name:
            return json.dumps({"error": "env_name parameter is required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            deployments = data.get("deployments", [])

            result = {
                "environment": env_name,
                "namespace": namespace,
                "applications": deployments,
                "count": len(deployments),
            }

            logger.info(f"Found {len(deployments)} applications in {namespace}")
            return json.dumps(result)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Environment '{env_name}' not found."})
        error_msg = f"Failed to list applications: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error listing applications: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_application_details(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Get detailed information about a specific application deployment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with application details, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace and deployment name
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{app_name}"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved details for {app_name} in {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to get application details: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting application details: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def scale_application(tool_context: ToolContext, env_name: str, app_name: str, replicas: int) -> str:
    """Scale an application deployment to a specific number of replicas.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        replicas: Number of replicas to scale to (must be >= 0)

    Returns:
        JSON string with scaling result, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        if replicas < 0:
            return json.dumps({"error": "Replicas must be >= 0."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{app_name}/scale"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            payload = {"replicas": replicas}
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Scaled {app_name} in {namespace} to {replicas} replicas")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to scale application: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error scaling application: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def restart_application(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Restart an application deployment by triggering a rollout restart.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with restart result, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{app_name}/restart"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.post(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Restarted {app_name} in {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to restart application: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error restarting application: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def update_application_image(
        tool_context: ToolContext,
        env_name: str,
        app_name: str,
        image: str,
        container: Optional[str] = None
) -> str:
    """Update the container image of an application deployment (rollout update).

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        image: New container image (e.g., "myapp:v2.0")
        container: Optional container name (if deployment has multiple containers)

    Returns:
        JSON string with update result, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name or not image:
            return json.dumps({"error": "env_name, app_name, and image parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{app_name}/rollout/update"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            payload = {"image": image}
            if container:
                payload["container"] = container
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Updated {app_name} in {namespace} to image {image}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to update application image: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error updating application image: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_application_status(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Get the rollout status of an application deployment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with rollout status, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{app_name}/rollout/status"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved rollout status for {app_name} in {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to get application status: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting application status: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_environment_metrics(tool_context: ToolContext, env_name: str) -> str:
    """Get pod metrics for an environment (CPU and memory usage).

    Args:
        tool_context: The ADK tool context
        env_name: Environment name

    Returns:
        JSON string with metrics data, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name:
            return json.dumps({"error": "env_name parameter is required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/metrics"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved metrics for {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Environment '{env_name}' not found."})
        elif e.response.status_code == 503:
            return json.dumps({"error": "Metrics service is unavailable. Please try again later."})
        error_msg = f"Failed to get metrics: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting environment metrics: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_environment_pods(tool_context: ToolContext, env_name: str) -> str:
    """Get all pods running in an environment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name

    Returns:
        JSON string with pod list, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name:
            return json.dumps({"error": "env_name parameter is required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/pods"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved pods for {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Environment '{env_name}' not found."})
        error_msg = f"Failed to get pods: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting environment pods: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def delete_environment(tool_context: ToolContext, env_name: str) -> str:
    """Delete an environment (namespace) and all its resources.

    WARNING: This is a destructive operation that will delete the entire environment
    including all applications, data, and configurations. Use with caution.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to delete

    Returns:
        JSON string with deletion result, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name:
            return json.dumps({"error": "env_name parameter is required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct namespace
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for deletion
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.delete(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Deleted environment {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"Environment '{env_name}' not found."})
        error_msg = f"Failed to delete environment: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error deleting environment: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


# ==================== User Application Management Operations ====================


async def list_user_apps(tool_context: ToolContext, env_name: str) -> str:
    """List all user applications deployed in a specific environment.

    User applications run in separate namespaces with pattern:
    client-1-{user}-{env}-{appname}

    This function lists all app namespaces for the given environment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name to list applications for

    Returns:
        JSON string with list of user applications, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name:
            return json.dumps({"error": "env_name parameter is required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request to get all namespaces
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            all_namespaces = data.get("namespaces", [])

            # Filter for user app namespaces: client-1-{user}-{env}-*
            app_namespace_prefix = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-"

            user_apps = []
            for ns in all_namespaces:
                ns_name = ns.get("name", "")
                if ns_name.startswith(app_namespace_prefix):
                    # Extract app name
                    app_name = ns_name.replace(app_namespace_prefix, "")
                    user_apps.append({
                        "app_name": app_name,
                        "namespace": ns_name,
                        "status": ns.get("status", "Unknown"),
                        "created_at": ns.get("created_at"),
                    })

            result = {
                "environment": env_name,
                "user_applications": user_apps,
                "count": len(user_apps),
            }

            logger.info(f"Found {len(user_apps)} user applications in environment {env_name}")
            return json.dumps(result)

    except httpx.HTTPStatusError as e:
        error_msg = f"Failed to list user applications: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error listing user applications: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_user_app_details(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Get detailed information about a specific user application deployment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with application details, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace: client-app-{user}-{env}-{app}
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"

        # Get all deployments in the app namespace
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            deployments = data.get("deployments", [])

            result = {
                "environment": env_name,
                "app_name": app_name,
                "namespace": namespace,
                "deployments": deployments,
                "deployment_count": len(deployments),
            }

            logger.info(f"Retrieved details for user app {app_name} in {namespace}")
            return json.dumps(result)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to get user application details: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting user application details: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def scale_user_app(tool_context: ToolContext, env_name: str, app_name: str, deployment_name: str, replicas: int) -> str:
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
    try:
        import httpx
        from application.services.resource_limit_service import get_resource_limit_service

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name or not deployment_name:
            return json.dumps({"error": "env_name, app_name, and deployment_name parameters are required."})

        # Check resource limits via limit service
        limit_service = get_resource_limit_service()
        limit_check = limit_service.check_replica_limit(
            user_id=user_id,
            env_name=env_name,
            app_name=app_name,
            requested_replicas=replicas
        )

        if not limit_check.allowed:
            error_msg = limit_service.format_limit_error(limit_check)
            logger.warning(f"Scale operation denied for user={user_id}: {limit_check.reason}")
            return json.dumps({
                "error": limit_check.reason,
                "limit": limit_check.limit_value,
                "requested": limit_check.current_value,
                "message": error_msg
            })

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{deployment_name}/scale"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            payload = {"replicas": replicas}
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Scaled user app {app_name}/{deployment_name} in {namespace} to {replicas} replicas")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' or deployment '{deployment_name}' not found."})
        error_msg = f"Failed to scale user application: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error scaling user application: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def restart_user_app(tool_context: ToolContext, env_name: str, app_name: str, deployment_name: str) -> str:
    """Restart a user application deployment by triggering a rollout restart.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        deployment_name: Name of the deployment within the app namespace to restart

    Returns:
        JSON string with restart result, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name or not deployment_name:
            return json.dumps({"error": "env_name, app_name, and deployment_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{deployment_name}/restart"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.post(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Restarted user app {app_name}/{deployment_name} in {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' or deployment '{deployment_name}' not found."})
        error_msg = f"Failed to restart user application: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error restarting user application: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


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
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name or not deployment_name or not image:
            return json.dumps({"error": "env_name, app_name, deployment_name, and image parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{deployment_name}/rollout/update"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            payload = {"image": image}
            if container:
                payload["container"] = container
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Updated user app {app_name}/{deployment_name} in {namespace} to image {image}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' or deployment '{deployment_name}' not found."})
        error_msg = f"Failed to update user application image: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error updating user application image: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_user_app_status(tool_context: ToolContext, env_name: str, app_name: str, deployment_name: str) -> str:
    """Get the rollout status of a user application deployment.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name
        deployment_name: Name of the deployment within the app namespace

    Returns:
        JSON string with rollout status, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name or not deployment_name:
            return json.dumps({"error": "env_name, app_name, and deployment_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/deployments/{deployment_name}/rollout/status"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved rollout status for user app {app_name}/{deployment_name} in {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' or deployment '{deployment_name}' not found."})
        error_msg = f"Failed to get user application status: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting user application status: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_user_app_metrics(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Get pod metrics for a user application (CPU and memory usage).

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with metrics data, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/metrics"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {"namespace": namespace}
            response = await client.get(api_url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved metrics for user app {app_name} in {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' not found in environment '{env_name}'."})
        elif e.response.status_code == 503:
            return json.dumps({"error": "Metrics service is unavailable. Please try again later."})
        error_msg = f"Failed to get user app metrics: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting user application metrics: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def get_user_app_pods(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Get all pods running in a user application namespace.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name

    Returns:
        JSON string with pod list, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}/pods"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved pods for user app {app_name} in {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to get user app pods: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error getting user application pods: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def delete_user_app(tool_context: ToolContext, env_name: str, app_name: str) -> str:
    """Delete a user application namespace and all its resources.

    WARNING: This is a destructive operation that will delete the entire user application
    namespace including all deployments, data, and configurations.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name
        app_name: Application name to delete

    Returns:
        JSON string with deletion result, or error message
    """
    try:
        import httpx

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return json.dumps({"error": "CLOUD_MANAGER_HOST environment variable not configured."})

        # Construct app namespace
        namespace = f"client-1-{_get_namespace(user_id)}-{_get_namespace(env_name)}-{_get_namespace(app_name)}"
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        api_url = f"{protocol}://{cloud_manager_host}/k8s/namespaces/{namespace}"

        # Get authentication token
        try:
            access_token = await _get_cloud_manager_auth_token()
        except Exception as e:
            return json.dumps({"error": f"Failed to authenticate with cloud manager: {str(e)}"})

        # Make API request
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for deletion
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.delete(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Deleted user application namespace {namespace}")
            return json.dumps(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps({"error": f"User application '{app_name}' not found in environment '{env_name}'."})
        error_msg = f"Failed to delete user application: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error deleting user application: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


# ==================== Log Management Operations ====================


async def search_logs(
    tool_context: ToolContext,
    env_name: str,
    app_name: str,
    query: Optional[str] = None,
    size: int = 50,
    time_range: Optional[str] = "15m"
) -> str:
    """Search logs in Elasticsearch for a specific environment and application.

    This function searches logs for the current user's namespaces in ELK.
    It supports searching both Cyoda environment logs (app_name="cyoda") and
    user application logs.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name (e.g., "dev", "staging", "prod")
        app_name: Application name (use "cyoda" for Cyoda platform logs)
        query: Optional search query string (Lucene syntax). If not provided, returns all logs.
        size: Number of log entries to return (default: 50, max: 1000)
        time_range: Time range for logs (default: "15m" for last 15 minutes)
                   Examples: "15m", "1h", "24h", "7d"

    Returns:
        JSON string with log search results, or error message

    Examples:
        - Search Cyoda platform logs: search_logs(env_name="dev", app_name="cyoda")
        - Search user app logs: search_logs(env_name="dev", app_name="my-calculator")
        - Search with query: search_logs(env_name="dev", app_name="cyoda", query="ERROR")
        - Custom time range: search_logs(env_name="dev", app_name="cyoda", time_range="1h")
    """
    try:
        import httpx
        import base64

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")
        if user_id.startswith("guest"):
            return json.dumps({"error": "User is not logged in. Please sign up or log in first."})

        if not env_name or not app_name:
            return json.dumps({"error": "Both env_name and app_name parameters are required."})

        # Limit size to prevent excessive results
        size = min(max(1, size), 50)

        # Get ELK configuration
        elk_host = os.getenv("ELK_HOST")
        elk_user = os.getenv("ELK_USER")
        elk_password = os.getenv("ELK_PASSWORD")

        if not all([elk_host, elk_user, elk_password]):
            return json.dumps({"error": "ELK configuration incomplete. Please configure ELK_HOST, ELK_USER, and ELK_PASSWORD."})

        # Construct index pattern based on namespace architecture
        org_id = _get_namespace(user_id)
        env = _get_namespace(env_name)

        if app_name.lower() == "cyoda":
            # Cyoda environment logs: logs-client-{user}-{env}*
            index_pattern = f"logs-client-{org_id}-{env}*"
        else:
            # User application logs: logs-client-1-{user}-{env}-{app}*
            app = _get_namespace(app_name)
            index_pattern = f"logs-client-1-{org_id}-{env}-{app}*"

        # Build Elasticsearch query
        es_query = {
            "size": size,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }

        # Add time range filter
        if time_range:
            es_query["query"] = {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{time_range}",
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            }
        else:
            es_query["query"] = {"bool": {"must": []}}

        # Add user query if provided
        if query:
            es_query["query"]["bool"]["must"].append({
                "query_string": {
                    "query": query,
                    "default_operator": "AND"
                }
            })

        # If no query and no time range, use match_all
        if not query and not time_range:
            es_query["query"] = {"match_all": {}}

        # Create basic auth header for ELK
        auth_string = f"{elk_user}:{elk_password}"
        auth_bytes = auth_string.encode('ascii')
        auth_header = base64.b64encode(auth_bytes).decode('ascii')

        # Make request to Elasticsearch
        search_url = f"https://{elk_host}/{index_pattern}/_search"

        logger.info(f"Searching logs for user={user_id}, env={env_name}, app={app_name}, index={index_pattern}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json"
            }
            response = await client.post(search_url, headers=headers, json=es_query)
            response.raise_for_status()

            result = response.json()

            # Extract relevant information from Elasticsearch response
            hits = result.get("hits", {})
            total_hits = hits.get("total", {}).get("value", 0)
            logs = []

            for hit in hits.get("hits", []):
                source = hit.get("_source", {})
                logs.append({
                    "timestamp": source.get("@timestamp"),
                    "level": source.get("level", "INFO"),
                    "message": source.get("message", ""),
                    "pod": source.get("kubernetes", {}).get("pod_name", "unknown"),
                    "container": source.get("kubernetes", {}).get("container_name", "unknown"),
                    "namespace": source.get("kubernetes", {}).get("namespace_name", "unknown"),
                })

            result_summary = {
                "environment": env_name,
                "app_name": app_name,
                "index_pattern": index_pattern,
                "total_hits": total_hits,
                "returned": len(logs),
                "time_range": time_range,
                "query": query,
                "logs": logs
            }

            logger.info(f"Found {total_hits} log entries for {env_name}/{app_name}, returning {len(logs)}")
            return json.dumps(result_summary)

    except httpx.HTTPStatusError as e:
        error_msg = f"Failed to search logs: {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return json.dumps({"error": error_msg, "details": e.response.text})
    except Exception as e:
        error_msg = f"Error searching logs: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})
