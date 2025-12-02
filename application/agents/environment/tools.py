"""Tools for the Environment Management agent."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from application.entity.conversation import Conversation
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def check_environment_exists(tool_context: ToolContext) -> str:
    """Check if a Cyoda environment exists for the current user.

    Attempts to access the user's environment URL to determine if it's deployed.
    This is useful for determining whether to issue credentials or deploy a new environment.

    Creates a cloud_window hook to open the Cloud/Environments panel in the UI.

    Args:
        tool_context: The ADK tool context

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

        if user_id.startswith("guest"):
            result = {
                "exists": False,
                "url": None,
                "message": "User is not logged in. Please sign up or log in first."
            }
            return json.dumps(result)

        # Construct environment URL
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        url = f"https://client-{user_id.lower()}.{client_host}"

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


async def deploy_cyoda_environment(
    tool_context: ToolContext, build_id: Optional[str] = None, env_name: Optional[str] = None
) -> str:
    """Deploy a new Cyoda environment for the user.

    Provisions a complete Cyoda environment including infrastructure,
    databases, and services. Creates a BackgroundTask entity to track deployment progress.

    Args:
      tool_context: The ADK tool context
      build_id: Optional build ID to associate with this deployment (e.g., from application build)
      env_name: Optional environment name/namespace to use for deployment

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

        if env_name:
            payload["env_name"] = env_name
            logger.info(f"Including env_name in deployment request: {env_name}")

        logger.info(
            f"Deploying Cyoda environment for user: {user_id}, chat_id: {chat_id}"
        )

        # Get cloud manager access token (temporary workaround)
        cloud_manager_api_key_encoded = os.getenv("CLOUD_MANAGER_API_KEY")
        cloud_manager_api_secret_encoded = os.getenv("CLOUD_MANAGER_API_SECRET")

        if not cloud_manager_api_key_encoded or not cloud_manager_api_secret_encoded:
            return "Error: Cloud manager credentials not configured. Please contact your administrator."

        # Decode base64 credentials
        cloud_manager_api_key = base64.b64decode(
            cloud_manager_api_key_encoded
        ).decode("utf-8")
        cloud_manager_api_secret = base64.b64decode(
            cloud_manager_api_secret_encoded
        ).decode("utf-8")

        # Authenticate with cloud manager (using separate auth subdomain)
        auth_url = f"{protocol}://cloud-manager-cyoda.kube3.cyoda.org/api/auth/login"
        auth_payload = {
            "username": cloud_manager_api_key,
            "password": cloud_manager_api_secret,
        }
        auth_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes for environment check
            # Get cloud manager token
            auth_response = await client.post(
                auth_url, json=auth_payload, headers=auth_headers
            )
            auth_response.raise_for_status()
            auth_data = auth_response.json()
            access_token = auth_data.get("token")

            if not access_token:
                return "Error: Failed to authenticate with cloud manager. Please contact your administrator."

            # Make deployment request with authentication
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.post(deploy_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            deployment_build_id = data.get("build_id")
            namespace = data.get("build_namespace")

            if not deployment_build_id or not namespace:
                return "Error: Deployment request succeeded but missing build information. Please try again."

            # Construct environment URL
            client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
            env_url = f"https://{namespace}.{client_host}"

            logger.info(
                f"Environment deployment started: build_id={deployment_build_id}, namespace={namespace}"
            )

            # Create BackgroundTask entity to track deployment progress
            task_id = None
            conversation_id = tool_context.state.get("conversation_id")

            if conversation_id:
                try:
                    from services.services import get_task_service

                    task_service = get_task_service()

                    logger.info(f"🔧 Creating BackgroundTask with user_id={user_id}, conversation_id={conversation_id}")

                    # Create background task with correct parameters
                    background_task = await task_service.create_task(
                        user_id=user_id,
                        task_type="environment_deployment",
                        name=f"Deploy Cyoda environment: {namespace}",
                        description=f"Deploying Cyoda environment to namespace {namespace}",
                        conversation_id=conversation_id,
                        build_id=deployment_build_id,
                        namespace=namespace,
                        env_url=env_url,
                    )

                    task_id = background_task.technical_id
                    logger.info(f"✅ Created BackgroundTask {task_id} for environment deployment")

                    # Update task to in_progress status
                    await task_service.update_task_status(
                        task_id=task_id,
                        status="in_progress",
                        message=f"Environment deployment started: {namespace}",
                        progress=10,
                        metadata={
                            "build_id": deployment_build_id,
                            "namespace": namespace,
                            "env_url": env_url,
                        },
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
                    logger.error(f"❌ Failed to create BackgroundTask for deployment: {e}", exc_info=True)
                    logger.error(f"❌ user_id={user_id}, conversation_id={conversation_id}, namespace={namespace}")
                    # Continue anyway - task tracking is not critical for deployment execution
            else:
                logger.warning(f"⚠️ No conversation_id in tool_context.state - cannot create BackgroundTask")

            # Store deployment info in session state
            tool_context.state["build_id"] = deployment_build_id
            tool_context.state["build_namespace"] = namespace
            tool_context.state["deployment_type"] = "cyoda_environment"
            tool_context.state["deployment_started"] = True
            tool_context.state["deployment_build_id"] = deployment_build_id
            tool_context.state["deployment_namespace"] = namespace

            # Also store build_id in Conversation's workflow_cache for persistence
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
                        conversation_data = conversation_response.data if isinstance(conversation_response.data, dict) else conversation_response.data.model_dump(by_alias=False)
                        conversation = Conversation(**conversation_data)

                        # Update workflow_cache with build_id
                        conversation.workflow_cache["build_id"] = deployment_build_id
                        conversation.workflow_cache["namespace"] = namespace
                        logger.info(f"📋 Updated workflow_cache with build_id={deployment_build_id}, namespace={namespace}")

                        # Update conversation
                        entity_dict = conversation.model_dump(by_alias=False)
                        await entity_service.update(
                            entity_id=conversation_id,
                            entity=entity_dict,
                            entity_class=Conversation.ENTITY_NAME,
                            entity_version=str(Conversation.ENTITY_VERSION),
                        )
                        logger.info(f"✅ Successfully updated conversation {conversation_id} with build_id in workflow_cache")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update conversation workflow_cache with build_id: {e}")
                    # Continue anyway - this is not critical for deployment

            # Start monitoring deployment progress in background
            if task_id:
                import asyncio
                asyncio.create_task(
                    _monitor_deployment_progress(
                        build_id=deployment_build_id,
                        task_id=task_id,
                        tool_context=tool_context,
                    )
                )
                logger.info(f"🔍 Started monitoring task for deployment {deployment_build_id}")

            # Create cloud window hook to open Environments panel
            if conversation_id:
                from application.agents.shared.hook_utils import (
                    create_cloud_window_hook,
                    create_background_task_hook,
                    create_combined_hook,
                )

                # Create cloud window hook
                cloud_hook = create_cloud_window_hook(
                    conversation_id=conversation_id,
                    environment_url=env_url,
                    environment_status="deploying",
                    message="Environment deployment started! Track progress in the Cloud panel.",
                )

                # If we have a task, combine with background task hook
                if task_id:
                    task_hook = create_background_task_hook(
                        task_id=task_id,
                        task_type="environment_deployment",
                        task_name=f"Deploy Cyoda environment: {namespace}",
                        task_description=f"Deploying Cyoda environment to namespace {namespace}",
                        conversation_id=conversation_id,
                        metadata={
                            "build_id": deployment_build_id,
                            "namespace": namespace,
                            "env_url": env_url,
                        },
                    )
                    # Combine both hooks
                    combined_hook = create_combined_hook(
                        code_changes_hook=cloud_hook,  # Reuse code_changes slot for cloud hook
                        background_task_hook=task_hook,
                    )
                    tool_context.state["last_tool_hook"] = combined_hook
                else:
                    # Just cloud window hook
                    tool_context.state["last_tool_hook"] = cloud_hook

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
    programming_language: str, repository_url: str, branch: str, is_public: bool = True
) -> str:
    """Deploy a user application to their Cyoda environment.

    Builds and deploys the user's application code to their provisioned
    Cyoda environment. Supports both Python and Java applications.

    Args:
      programming_language: Either "PYTHON" or "JAVA"
      repository_url: Git repository URL containing the application code
      branch: Git branch to deploy (e.g., "main", "develop")
      is_public: Whether the repository is public (default: True)

    Returns:
      Success message with deployment details, or error message
    """
    try:
        import httpx

        # Validate programming language
        programming_language = programming_language.upper()
        if programming_language not in ["PYTHON", "JAVA"]:
            return f"Error: Unsupported programming language '{programming_language}'. Supported languages: PYTHON, JAVA"

        # Get cloud manager configuration
        cloud_manager_host = os.getenv("CLOUD_MANAGER_HOST")
        if not cloud_manager_host:
            return "Error: CLOUD_MANAGER_HOST environment variable not configured. Please contact your administrator."

        # Construct deployment URL
        protocol = "http" if "localhost" in cloud_manager_host else "https"
        deploy_url = os.getenv(
            "DEPLOY_USER_APP", f"{protocol}://{cloud_manager_host}/deploy/user-app"
        )

        # Prepare deployment payload
        payload = {
            "programming_language": programming_language,
            "repository_url": repository_url,
            "branch": branch,
            "is_public": str(is_public).lower(),
        }

        # Add installation ID for public repos
        if is_public:
            installation_id = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")
            if installation_id:
                payload["installation_id"] = installation_id

        logger.info(
            f"Deploying {programming_language} application from {repository_url}@{branch}"
        )

        # Make deployment request
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes for deployment
            response = await client.post(deploy_url, json=payload)
            response.raise_for_status()

            data = response.json()
            build_id = data.get("build_id")

            if not build_id:
                return "Error: Deployment request succeeded but missing build ID. Please try again."

            logger.info(f"Application deployment started: build_id={build_id}")

            return f"""✓ Application deployment started successfully!

**Build ID:** {build_id}
**Language:** {programming_language}
**Repository:** {repository_url}
**Branch:** {branch}

Your application is being built and deployed. This typically takes 3-5 minutes.

You can check the deployment status by asking:
- "What's my deployment status?"
- "Check deployment status for build {build_id}"
- "Show me the build logs for {build_id}"

I'll keep you updated on the progress!"""

    except httpx.HTTPStatusError as e:
        error_msg = f"Deployment request failed with status {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return f"Error: {error_msg}. Please verify your repository URL and try again."
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
        import base64

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

        # Get cloud manager access token (temporary workaround)
        cloud_manager_api_key_encoded = os.getenv("CLOUD_MANAGER_API_KEY")
        cloud_manager_api_secret_encoded = os.getenv("CLOUD_MANAGER_API_SECRET")

        if not cloud_manager_api_key_encoded or not cloud_manager_api_secret_encoded:
            return "Error: Cloud manager credentials not configured."

        # Decode base64 credentials
        cloud_manager_api_key = base64.b64decode(
            cloud_manager_api_key_encoded
        ).decode("utf-8")
        cloud_manager_api_secret = base64.b64decode(
            cloud_manager_api_secret_encoded
        ).decode("utf-8")

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

        with httpx.Client(timeout=30.0) as client:
            # Get cloud manager token
            auth_response = client.post(
                auth_url, json=auth_payload, headers=auth_headers
            )
            auth_response.raise_for_status()
            auth_data = auth_response.json()
            access_token = auth_data.get("token")

            if not access_token:
                return "Error: Failed to authenticate with cloud manager."

            # Make status request with authentication
            headers = {"Authorization": f"Bearer {access_token}"}
            response = client.get(f"{status_url}?build_id={build_id}", headers=headers)
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


async def ui_function_issue_technical_user(tool_context: ToolContext) -> str:
    """Issue M2M (machine-to-machine) technical user credentials.

    This function stores a UI function call instruction in the tool context
    that tells the frontend to make an API call to issue technical user credentials
    (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication.

    The UI function JSON will be added to the conversation by the agent framework
    after the agent completes its response, preventing race conditions.

    Use this tool when the user asks for credentials or needs to authenticate
    their application with the Cyoda environment.

    Args:
        tool_context: The ADK tool context (auto-injected)

    Returns:
        Success message confirming credential issuance was initiated
    """
    try:
        # Create UI function parameters
        ui_params = {
            "type": "ui_function",
            "function": "ui_function_issue_technical_user",
            "method": "POST",
            "path": "/api/users",
            "response_format": "json",
        }

        logger.info(f"Storing UI function in tool context: {json.dumps(ui_params)}")

        # Store UI function in tool context so the agent framework can add it to conversation
        # This prevents race conditions where both the tool and route handler update the conversation
        if "ui_functions" not in tool_context.state:
            tool_context.state["ui_functions"] = []
        tool_context.state["ui_functions"].append(ui_params)

        logger.info(f"✅ UI function stored in context, will be added to conversation after agent response")

        return "✅ Credential issuance initiated. The UI will create your M2M technical user credentials (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication."

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
