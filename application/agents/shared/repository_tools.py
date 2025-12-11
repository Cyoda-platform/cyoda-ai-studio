

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from google.adk.tools.tool_context import ToolContext
from google.genai import types

from application.agents.shared.prompt_loader import load_template
from application.entity.conversation.version_1.conversation import Conversation
from application.services.github.auth.installation_token_manager import InstallationTokenManager
from application.services.github.repository.url_parser import parse_repository_url
from common.exception.exceptions import InvalidTokenException
from common.utils.utils import send_get_request
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def _update_conversation_with_lock(
    conversation_id: str,
    update_fn: callable,
    description: str = "update"
) -> bool:
    """
    Update a conversation entity with pessimistic locking.

    This is a centralized locking mechanism that should be used for ALL conversation updates
    to prevent race conditions when multiple agents/processes update the same conversation.

    Args:
        conversation_id: Technical ID of the conversation
        update_fn: Function that takes a Conversation object and modifies it in-place
        description: Description of the update for logging

    Returns:
        True if update succeeded, False otherwise
    """
    max_retries = 10
    retry_delay = 0.2  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"🔒 [{description}] Attempting to acquire lock (attempt {attempt + 1}/{max_retries}): conversation_id={conversation_id}")
            entity_service = get_entity_service()

            # STEP 1: Get FRESH conversation data before any operation
            logger.info(f"📥 [{description}] Fetching fresh conversation data...")
            response = await entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not response or not response.data:
                logger.warning(f"⚠️ Conversation {conversation_id} not found")
                return False

            conversation_data = response.data if isinstance(response.data, dict) else response.data.model_dump(by_alias=False)
            conversation = Conversation(**conversation_data)

            # Log current state BEFORE any changes
            logger.info(f"📊 [{description}] BEFORE update - repositoryName={conversation.repository_name}, repositoryOwner={conversation.repository_owner}, repositoryBranch={conversation.repository_branch}, locked={conversation.locked}")

            # Check if already locked by another process
            if conversation.locked:
                logger.warning(f"🔒 [{description}] Conversation {conversation_id} is locked, waiting {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 2.0)  # Exponential backoff, max 2s
                continue

            # STEP 2: Acquire lock
            conversation.locked = True
            entity_dict = conversation.model_dump(by_alias=False)

            try:
                logger.info(f"🔒 [{description}] Sending lock acquisition request for conversation {conversation_id}...")
                lock_response = await entity_service.update(
                    entity_id=conversation_id,
                    entity=entity_dict,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
                logger.info(f"🔒 [{description}] Lock acquisition response: {lock_response}")
                logger.info(f"🔒 [{description}] Lock acquired for conversation {conversation_id}")
            except Exception as lock_error:
                # Failed to acquire lock (version conflict) - another process got it first
                logger.warning(f"⚠️ [{description}] Failed to acquire lock (version conflict): {lock_error}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 2.0)
                continue

            # STEP 3: Now we have the lock - fetch FRESH data again and update
            try:
                # Get fresh conversation data (important: another process might have updated while we were acquiring lock)
                logger.info(f"📥 [{description}] Fetching fresh conversation data after lock acquisition...")
                response = await entity_service.get_by_id(
                    entity_id=conversation_id,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                conversation_data = response.data if isinstance(response.data, dict) else response.data.model_dump(by_alias=False)
                conversation = Conversation(**conversation_data)

                # Apply the update function
                update_fn(conversation)

                # Release lock
                conversation.locked = False

                # Update conversation
                entity_dict = conversation.model_dump(by_alias=False)

                # Debug: Log what we're sending
                logger.info(f"🔍 [{description}] Sending update request with locked=False...")
                logger.info(f"🔍 [{description}] Entity dict keys: {list(entity_dict.keys())}")
                logger.info(f"🔍 [{description}] Sending - repositoryName={entity_dict.get('repositoryName')}, repositoryOwner={entity_dict.get('repositoryOwner')}, repositoryBranch={entity_dict.get('repositoryBranch')}")

                update_response = await entity_service.update(
                    entity_id=conversation_id,
                    entity=entity_dict,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                logger.info(f"✅ [{description}] Update response: {update_response}")

                # STEP 4: VERIFY - Fetch entity immediately after update to confirm persistence
                logger.info(f"🔍 [{description}] Verifying update by fetching entity...")
                verify_response = await entity_service.get_by_id(
                    entity_id=conversation_id,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                if verify_response and verify_response.data:
                    verify_data = verify_response.data if isinstance(verify_response.data, dict) else verify_response.data.model_dump(by_alias=False)
                    logger.info(f"✅ [{description}] VERIFICATION - repositoryName={verify_data.get('repositoryName')}, repositoryOwner={verify_data.get('repositoryOwner')}, repositoryBranch={verify_data.get('repositoryBranch')}, locked={verify_data.get('locked')}")

                    # Check if fields were actually persisted
                    if entity_dict.get('repositoryName') and not verify_data.get('repositoryName'):
                        logger.error(f"❌ [{description}] VERIFICATION FAILED: repositoryName was not persisted! Sent: {entity_dict.get('repositoryName')}, Got: {verify_data.get('repositoryName')}")
                    if entity_dict.get('repositoryOwner') and not verify_data.get('repositoryOwner'):
                        logger.error(f"❌ [{description}] VERIFICATION FAILED: repositoryOwner was not persisted! Sent: {entity_dict.get('repositoryOwner')}, Got: {verify_data.get('repositoryOwner')}")
                    if entity_dict.get('repositoryBranch') and not verify_data.get('repositoryBranch'):
                        logger.error(f"❌ [{description}] VERIFICATION FAILED: repositoryBranch was not persisted! Sent: {entity_dict.get('repositoryBranch')}, Got: {verify_data.get('repositoryBranch')}")
                else:
                    logger.warning(f"⚠️ [{description}] Could not verify update - entity not found")

                logger.info(f"✅ [{description}] Successfully updated conversation {conversation_id} (lock released)")
                return True  # Success

            except Exception as update_error:
                # Failed to update - release lock
                logger.error(f"❌ [{description}] Failed to update conversation, releasing lock: {update_error}", exc_info=True)
                try:
                    logger.info(f"🔓 [{description}] Attempting to release lock...")
                    response = await entity_service.get_by_id(
                        entity_id=conversation_id,
                        entity_class=Conversation.ENTITY_NAME,
                        entity_version=str(Conversation.ENTITY_VERSION),
                    )
                    conversation_data = response.data if isinstance(response.data, dict) else response.data.model_dump(by_alias=False)
                    conversation = Conversation(**conversation_data)
                    conversation.locked = False
                    entity_dict = conversation.model_dump(by_alias=False)
                    release_response = await entity_service.update(
                        entity_id=conversation_id,
                        entity=entity_dict,
                        entity_class=Conversation.ENTITY_NAME,
                        entity_version=str(Conversation.ENTITY_VERSION),
                    )
                    logger.info(f"🔓 [{description}] Lock release response: {release_response}")
                    logger.info(f"🔓 [{description}] Released lock after error")
                except Exception as release_error:
                    logger.error(f"❌ [{description}] Failed to release lock after error: {release_error}", exc_info=True)

                # Retry
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 2.0)
                continue

        except Exception as e:
            logger.error(f"❌ [{description}] Unexpected error in lock acquisition: {e}", exc_info=True)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 2.0)
            continue

    logger.error(f"❌ [{description}] Failed to update conversation after {max_retries} attempts")
    return False


async def _update_conversation_build_context(
    conversation_id: str, language: str, branch_name: str, repository_name: str
) -> None:
    """
    Update conversation's workflow_cache with build context AND root-level repository fields.

    This allows the setup agent to retrieve build context when invoked manually,
    and enables the frontend to automatically open the GitHub canvas.

    Args:
        conversation_id: Technical ID of the conversation
        language: Programming language (python or java)
        branch_name: Git branch name
        repository_name: GitHub repository name
    """
    def update_fn(conversation: Conversation) -> None:
        # Update workflow_cache with build context AND repository info
        # NOTE: Repository fields (repositoryName, repositoryOwner, repositoryBranch) are not in Cyoda schema,
        # so we store them in workflowCache which IS persisted
        repository_owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")

        conversation.workflow_cache["language"] = language
        conversation.workflow_cache["branch_name"] = branch_name
        conversation.workflow_cache["repository_name"] = repository_name
        conversation.workflow_cache["repository_owner"] = repository_owner
        conversation.workflow_cache["repository_branch"] = branch_name

        logger.info(f"📋 Updated workflow_cache with language={language}, branch_name={branch_name}")
        logger.info(f"📦 Updated workflow_cache with repository info: {repository_owner}/{repository_name}@{branch_name}")

        # Also update root-level fields (for Pydantic model compatibility, even though they won't persist in Cyoda)
        conversation.repository_name = repository_name
        conversation.repository_owner = repository_owner
        conversation.repository_branch = branch_name

    success = await _update_conversation_with_lock(
        conversation_id,
        update_fn,
        description="build_context"
    )

    if not success:
        logger.error(f"❌ Failed to update conversation build context for {conversation_id}")


async def _add_task_to_conversation(conversation_id: str, task_id: str) -> None:
    """
    Add a background task ID to the conversation's background_task_ids list.

    Args:
        conversation_id: Technical ID of the conversation
        task_id: Technical ID of the background task to add
    """
    logger.info(f"🔍 _add_task_to_conversation called: conversation_id={conversation_id}, task_id={task_id}")

    def update_fn(conversation: Conversation) -> None:
        # Add task ID to background_task_ids list (root-level field in schema)
        if task_id not in conversation.background_task_ids:
            conversation.background_task_ids.append(task_id)
            logger.info(f"📋 Added task {task_id} to background_task_ids. Total: {len(conversation.background_task_ids)}")
        else:
            logger.info(f"ℹ️ Task {task_id} already in conversation {conversation_id}")

    success = await _update_conversation_with_lock(
        conversation_id,
        update_fn,
        description=f"add_task_{task_id[:8]}"
    )

    if not success:
        error_msg = f"Failed to add task {task_id} to conversation {conversation_id}"
        logger.error(f"❌ {error_msg}")
        raise RuntimeError(error_msg)


# Template repository URLs (used for cloning the initial template)
JAVA_TEMPLATE_REPO = "https://github.com/Cyoda-platform/java-client-template"
PYTHON_TEMPLATE_REPO = "https://github.com/Cyoda-platform/mcp-cyoda-quart-app"

# GitHub configuration from environment
# Public repository URLs (where we push the code for public builds)
PYTHON_PUBLIC_REPO_URL = os.getenv("PYTHON_PUBLIC_REPO_URL", PYTHON_TEMPLATE_REPO)
JAVA_PUBLIC_REPO_URL = os.getenv("JAVA_PUBLIC_REPO_URL", JAVA_TEMPLATE_REPO)
GITHUB_PUBLIC_REPO_INSTALLATION_ID = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")

# Protected branches - NEVER use these for builds
PROTECTED_BRANCHES = {"main", "master", "develop", "development", "production", "prod"}


async def generate_branch_uuid() -> str:
    """
    Generate a UUID-based branch name for public repositories.

    This function generates unique branch names to avoid conflicts in public repositories.
    Use this for public repositories where you need unique branch names.

    Returns:
        UUID string in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

    Example:
        branch_name = generate_branch_uuid()
        # Returns: "68f71074-c15f-11f0-89a7-40c2ba0ac9eb"
    """
    return str(uuid.uuid4())


async def check_existing_branch_configuration(
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Check if a branch is already configured in the current conversation.

    This function checks the conversation entity for existing repository configuration
    to avoid unnecessary re-cloning when a branch is already set up.

    Args:
        tool_context: Execution context (auto-injected)

    Returns:
        JSON string with configuration status and details

    Example:
        result = await check_existing_branch_configuration()
        # Returns: {"configured": true, "language": "python", "branch_name": "uuid", ...}
    """
    try:
        if not tool_context:
            return json.dumps({
                "configured": False,
                "error": "Tool context not available"
            })

        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return json.dumps({
                "configured": False,
                "error": "No conversation_id found in context"
            })

        # FIRST: Try to get repository info from tool_context.state (agent's thinking stream)
        # This is the most up-to-date source and avoids race conditions
        repository_name = tool_context.state.get("repository_name")
        repository_owner = tool_context.state.get("repository_owner")
        repository_branch = tool_context.state.get("branch_name")
        repository_url = tool_context.state.get("repository_url")
        installation_id = tool_context.state.get("installation_id")
        repository_path = tool_context.state.get("repository_path")

        # FALLBACK: If not in context state, get from Conversation entity
        if not repository_name or not repository_branch:
            entity_service = get_entity_service()
            conversation_response = await entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not conversation_response:
                return json.dumps({
                    "configured": False,
                    "error": f"Conversation {conversation_id} not found"
                })

            # Handle conversation data (can be dict or object)
            conversation_data = conversation_response.data
            if isinstance(conversation_data, dict):
                repository_name = repository_name or conversation_data.get('repository_name')
                repository_owner = repository_owner or conversation_data.get('repository_owner')
                repository_branch = repository_branch or conversation_data.get('repository_branch')
                repository_url = repository_url or conversation_data.get('repository_url')
                installation_id = installation_id or conversation_data.get('installation_id')
            else:
                repository_name = repository_name or getattr(conversation_data, 'repository_name', None)
                repository_owner = repository_owner or getattr(conversation_data, 'repository_owner', None)
                repository_branch = repository_branch or getattr(conversation_data, 'repository_branch', None)
                repository_url = repository_url or getattr(conversation_data, 'repository_url', None)
                installation_id = installation_id or getattr(conversation_data, 'installation_id', None)

        # Check if branch is configured
        if repository_name and repository_branch:
            # Determine language from repository name
            language = None
            if repository_name == "mcp-cyoda-quart-app":
                language = "python"
            elif repository_name == "java-client-template":
                language = "java"
            elif "python" in repository_name.lower():
                language = "python"
            elif "java" in repository_name.lower():
                language = "java"

            # Determine repository type
            repository_type = "private" if repository_url and installation_id else "public"

            logger.info(f"✅ Found existing branch configuration: {repository_owner}/{repository_name}@{repository_branch}")

            return json.dumps({
                "configured": True,
                "language": language,
                "repository_type": repository_type,
                "repository_name": repository_name,
                "repository_owner": repository_owner,
                "repository_branch": repository_branch,
                "repository_url": repository_url,
                "installation_id": installation_id,
                "repository_path": repository_path,
                "ready_to_build": bool(repository_path)  # True if repository is cloned locally
            })
        else:
            return json.dumps({
                "configured": False,
                "message": "No branch configuration found in conversation"
            })

    except Exception as e:
        logger.error(f"Error checking existing branch configuration: {e}", exc_info=True)
        return json.dumps({
            "configured": False,
            "error": str(e)
        })


async def _is_protected_branch(branch_name: str) -> bool:
    """
    Check if a branch name is protected.

    Protected branches (main, master, develop, etc.) should NEVER be used for builds.

    Args:
        branch_name: Branch name to check

    Returns:
        True if branch is protected, False otherwise
    """
    return branch_name.lower().strip() in PROTECTED_BRANCHES


async def _get_authenticated_repo_url_sync(repository_url: str, installation_id: str) -> str:
    """
    Get authenticated repository URL for git operations (fully async).

    Args:
        repository_url: Repository URL (e.g., "https://github.com/owner/repo")
        installation_id: GitHub App installation ID

    Returns:
        Authenticated URL (e.g., "https://x-access-token:TOKEN@github.com/owner/repo.git")
    """
    try:
        # Get token asynchronously (no blocking!)
        token_manager = InstallationTokenManager()
        token = await token_manager.get_installation_token(int(installation_id))

        # Parse URL and create authenticated version
        url_info = parse_repository_url(repository_url)
        authenticated_url = url_info.to_authenticated_url(token)

        logger.info(f"✅ Generated authenticated URL for {url_info.owner}/{url_info.repo_name}")
        return authenticated_url

    except Exception as e:
        logger.error(f"❌ Failed to generate authenticated URL: {e}")
        # Return original URL as fallback (will likely fail for private repos)
        return repository_url

# Augment CLI configuration
# Use mock script for testing (doesn't require API credentials)
# Change to augment_build.sh for real Augment CLI execution

# Get the directory where this module is located
_MODULE_DIR = Path(__file__).parent

# Default script path (relative to this module)
_DEFAULT_SCRIPT = _MODULE_DIR / "augment_build_mock.sh"

# Allow override via environment variable (can be absolute or relative to project root)
AUGMENT_CLI_SCRIPT = os.getenv("AUGMENT_CLI_SCRIPT", str(_DEFAULT_SCRIPT))





# _update_conversation_status function removed - all progress updates now go to BackgroundTask entity only  # Give up

async def check_user_environment_status(
    tool_context: Optional[ToolContext] = None
) -> str:
    """
    Check if the user's Cyoda environment is deployed and ready.

    This function automatically checks the deployment status without requiring
    user confirmation. It returns structured information about the environment.

    Args:
        tool_context: Execution context (auto-injected)

    Returns:
        Status message indicating if environment is deployed or needs deployment
    """
    try:
        if not tool_context:
            return "ERROR: tool_context not available"

        # Get user_id from context
        user_id = tool_context.state.get("user_id", "guest")
        is_guest = user_id.startswith("guest.")

        # Check if deployment was started in this session
        deployment_started = tool_context.state.get("deployment_started", False)
        deployment_build_id = tool_context.state.get("deployment_build_id")
        deployment_namespace = tool_context.state.get("deployment_namespace")

        # Check if we're in test/mock mode
        mock_mode = os.getenv("MOCK_ENVIRONMENT_CHECK", "false").lower() == "true"

        if mock_mode:
            # In mock mode, always return DEPLOYED for testing
            logger.info(f"Mock mode enabled - returning DEPLOYED for user {user_id}")
            client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
            url = f"https://client-{user_id.lower()}.{client_host}"
            tool_context.state["cyoda_env_url"] = url
            tool_context.state["cyoda_env_deployed"] = True
            return f"DEPLOYED: Your Cyoda environment is already deployed at {url}. Ready to build your application."

        if is_guest:
            logger.info(f"Guest user detected: {user_id}")
            return "NEEDS_LOGIN: User is not logged in. Please log in to deploy a Cyoda environment."

        # If deployment was started in this session, inform user it's in progress
        if deployment_started and deployment_build_id:
            logger.info(f"Deployment in progress for user {user_id}: Build ID {deployment_build_id}")
            return f"DEPLOYING: Your Cyoda environment deployment is in progress (Build ID: {deployment_build_id}, Namespace: {deployment_namespace}). Deployment typically takes 5-10 minutes. Your application build has already started and will be ready when deployment completes."

        # Construct environment URL
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        url = f"https://client-{user_id.lower()}.{client_host}"
        deployed = False

        try:
            # Try to access the environment API to check if it's deployed
            await send_get_request(api_url=url, path="api/v1", token="guest_token")
        except InvalidTokenException:
            # InvalidTokenException means the environment exists and is responding
            deployed = True
            logger.info(f"✅ Environment deployed for user {user_id}: {url}")
        except Exception as e:
            # Any other exception means environment is not deployed
            logger.info(f"Environment not deployed for user {user_id}: {e}")
            deployed = False

        # Store environment info in context
        tool_context.state["cyoda_env_url"] = url
        tool_context.state["cyoda_env_deployed"] = deployed

        if deployed:
            return f"DEPLOYED: Your Cyoda environment is already deployed at {url}. Ready to build your application."
        else:
            return f"NOT_DEPLOYED: Your Cyoda environment is not yet deployed. URL will be: {url}"

    except Exception as e:
        logger.error(f"Error checking environment status: {e}", exc_info=True)
        return f"ERROR: Failed to check environment status: {str(e)}"


async def ask_user_to_select_option(
    question: str,
    options: Optional[list[Dict[str, str]]] = None,
    selection_type: str = "single",
    context: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Show interactive UI for the user to select from a list of options.

    This is a generic tool that can be used whenever you need to ask the user to choose from multiple options.
    The UI will display clickable buttons or checkboxes for the user to make their selection.

    **WHEN TO USE:**
    - When you need to ask the user to choose from a list of options
    - Instead of asking the user to type their choice
    - For any question with 2 or more predefined options

    **AFTER CALLING THIS TOOL:**
    - Wait for the user's response
    - The response will contain the selected option label(s)
    - Parse the response and proceed with your workflow

    Args:
        question: The question to ask the user
        options: List of option dictionaries, each with:
            - value: The value to return when selected (required)
            - label: Display text for the option (required)
            - description: Optional description text (optional)
            If not provided, returns an error message with instructions.
        selection_type: Either "single" (radio buttons) or "multiple" (checkboxes). Default: "single"
        context: Optional additional context or information to display
        tool_context: Execution context (auto-injected)

    Returns:
        Message with hook for UI to display selection interface

    Examples:
        # Example 1: Ask user to choose between new or existing branch
        result = ask_user_to_select_option(
            question="Would you like to create a new branch or use an existing one?",
            options=[
                {
                    "value": "new_branch",
                    "label": "Create a new branch",
                    "description": "Start fresh with a new branch for your application"
                },
                {
                    "value": "existing_branch",
                    "label": "Use an existing branch",
                    "description": "Continue working on a branch you've already created"
                }
            ],
            selection_type="single"
        )

        # Example 2: Ask user to select features for their app
        result = ask_user_to_select_option(
            question="Which features would you like to include in your e-commerce application?",
            options=[
                {"value": "cart", "label": "Shopping Cart", "description": "Add items to cart and checkout"},
                {"value": "payment", "label": "Payment Processing", "description": "Accept credit card payments"},
                {"value": "inventory", "label": "Inventory Tracking", "description": "Track product stock levels"},
                {"value": "orders", "label": "Order Management", "description": "Manage customer orders"}
            ],
            selection_type="multiple",
            context="Select all features you want to include. You can add more features later."
        )
    """
    if not tool_context:
        return "ERROR: Tool context not available. This function must be called within a conversation context."

    # If options not provided, return helpful error with example
    if not options or len(options) == 0:
        example = """ERROR: The 'options' parameter is required. Here's an example of how to call this tool:

ask_user_to_select_option(
    question="Which option would you prefer?",
    options=[
        {"value": "opt1", "label": "Option 1", "description": "Description for option 1"},
        {"value": "opt2", "label": "Option 2", "description": "Description for option 2"}
    ],
    selection_type="single"
)

Each option must have:
- 'value': A unique identifier for the option
- 'label': Display text shown to the user
- 'description': (optional) Additional context for the option"""
        return example

    # Validate each option
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
        selection_type=selection_type,
        context=context,
    )

    # Store hook in context for SSE streaming
    tool_context.state["last_tool_hook"] = hook

    # Return message with hook
    message = f"{question}\n\nPlease select your choice(s) using the options below."

    return wrap_response_with_hook(message, hook)


async def set_repository_config(
    repository_type: str,
    installation_id: Optional[str] = None,
    repository_url: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Configure repository settings for the build.

    **REQUIRED** before using clone_repository or commit_and_push_changes.

    Args:
        repository_type: Either "public" or "private"
            - "public": Use Cyoda's public template repositories (mcp-cyoda-quart-app, java-client-template)
            - "private": Use your own private repository (requires GitHub App installation)
        installation_id: GitHub App installation ID (required for private repos only)
        repository_url: Your repository URL like "https://github.com/owner/repo" (required for private repos only)
        tool_context: Execution context (auto-injected)

    Returns:
        Confirmation message

    Examples:
        # For public repositories (using Cyoda templates):
        set_repository_config(repository_type="public")

        # For private repositories:
        set_repository_config(
            repository_type="private",
            installation_id="12345678",
            repository_url="https://github.com/myorg/my-repo"
        )
    """
    if repository_type not in ["public", "private"]:
        return (
            f"ERROR: repository_type must be 'public' or 'private', got '{repository_type}'.\n\n"
            f"Use:\n"
            f"- 'public' for Cyoda template repositories\n"
            f"- 'private' for your own repositories"
        )

    if not tool_context:
        return "ERROR: Tool context not available. This function must be called within a conversation context."

    tool_context.state["repository_type"] = repository_type

    if repository_type == "private":
        if not installation_id or not repository_url:
            return (
                f"ERROR: For private repositories, both installation_id and repository_url are required.\n\n"
                f"Example:\n"
                f"set_repository_config(\n"
                f"    repository_type='private',\n"
                f"    installation_id='12345678',\n"
                f"    repository_url='https://github.com/myorg/my-repo'\n"
                f")\n\n"
                f"💡 To get your installation_id, install the Cyoda AI Assistant GitHub App on your repository."
            )

        tool_context.state["installation_id"] = installation_id
        tool_context.state["user_repository_url"] = repository_url

        logger.info(f"✅ Private repository configured: {repository_url}, installation_id={installation_id}")
        return (
            f"✅ **Private Repository Configured**\n\n"
            f"Repository: {repository_url}\n"
            f"Installation ID: {installation_id}\n\n"
            f"You can now use `clone_repository()` to clone and work with your private repository."
        )
    else:
        # Public repository - will use GITHUB_PUBLIC_REPO_INSTALLATION_ID from env
        if not GITHUB_PUBLIC_REPO_INSTALLATION_ID:
            return (
                f"ERROR: Public repository mode is not available.\n\n"
                f"The GITHUB_PUBLIC_REPO_INSTALLATION_ID environment variable is not configured. "
                f"Please use private repository mode instead."
            )

        logger.info(f"✅ Public repository mode configured")
        return (
            f"✅ **Public Repository Mode Configured**\n\n"
            f"Template repositories:\n"
            f"- Python: {PYTHON_PUBLIC_REPO_URL}\n"
            f"- Java: {JAVA_PUBLIC_REPO_URL}\n\n"
            f"You can now use `clone_repository()` to clone and work with Cyoda template repositories."
        )

    return "ERROR: tool_context not available"





async def _run_git_command(
    cmd: list[str],
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Run a git command asynchronously.

    Args:
        cmd: Command as list of strings
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
        return process.returncode, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", str(e)


async def clone_repository(
    language: str,
    branch_name: str,
    target_directory: Optional[str] = None,
    use_existing_branch: bool = False,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Clone repository based on programming language and create a new branch or checkout existing branch.

    **IMPORTANT**: You must call set_repository_config() first to specify whether you want to use:
    - Public repositories (Cyoda templates)
    - Private repositories (your own repos)

    Args:
        language: Programming language ('java' or 'python')
        branch_name: Branch name to create/checkout (will be pushed to remote if new)
        target_directory: Optional target directory (defaults to /tmp/cyoda_builds/<branch_name>)
        use_existing_branch: If True, checkout existing branch instead of creating new one (default: False)
        tool_context: Execution context (auto-injected)

    Returns:
        Status message with repository path, or error if repository not configured

    Example:
        # First configure repository type:
        set_repository_config(repository_type="public")
        # Then clone and create new branch:
        clone_repository("python", "my-feature-branch")
        # Or checkout existing branch:
        clone_repository("python", "existing-branch", use_existing_branch=True)
    """
    try:
        # CRITICAL: Validate branch name is not protected
        if await _is_protected_branch(branch_name):
            error_msg = (
                f"🚫 CRITICAL ERROR: Cannot use protected branch '{branch_name}'. "
                f"Protected branches ({', '.join(sorted(PROTECTED_BRANCHES))}) must NEVER be used for builds. "
                f"Please use generate_branch_uuid() to create a unique branch name."
            )
            logger.error(error_msg)
            return f"ERROR: {error_msg}"

        # Get user's repository information from context
        user_repo_url = None
        installation_id = None
        base_branch = "main"  # Default base branch

        if tool_context:
            repo_type = tool_context.state.get("repository_type")  # "public" or "private"

            if repo_type == "private":
                # For private repos, get user-provided repository URL and installation ID
                user_repo_url = tool_context.state.get("user_repository_url")
                installation_id = tool_context.state.get("installation_id")
                logger.info(f"📦 Private repo mode: {user_repo_url}, installation_id={installation_id}")
            elif repo_type == "public":
                # For public repos, use the configured public repository URL from .env
                if language.lower() == "python":
                    user_repo_url = PYTHON_PUBLIC_REPO_URL
                elif language.lower() == "java":
                    user_repo_url = JAVA_PUBLIC_REPO_URL
                installation_id = GITHUB_PUBLIC_REPO_INSTALLATION_ID
                logger.info(f"📦 Public repo mode: {user_repo_url}, installation_id={installation_id}")
            elif repo_type is None:
                # No repository type specified - require explicit configuration
                error_msg = (
                    f"❌ Repository configuration required before cloning.\n\n"
                    f"Please specify your repository type first:\n\n"
                    f"**For Public Repositories (Cyoda templates):**\n"
                    f"Use: `set_repository_config(repository_type='public')`\n"
                    f"This will use Cyoda's public templates and push to the public repository.\n\n"
                    f"**For Private Repositories:**\n"
                    f"Use: `set_repository_config(repository_type='private', installation_id='YOUR_ID', repository_url='YOUR_REPO_URL')`\n"
                    f"This requires your GitHub App to be installed on your private repository.\n\n"
                    f"💡 **Need help?** The repository type determines where your code will be stored and pushed."
                )
                logger.warning(f"⚠️ No repository type specified for branch {branch_name}")
                return f"ERROR: {error_msg}"
            else:
                error_msg = f"Invalid repository_type '{repo_type}'. Must be 'public' or 'private'."
                logger.error(error_msg)
                return f"ERROR: {error_msg}"
        else:
            # No tool context - cannot proceed without configuration
            error_msg = (
                f"❌ Repository configuration required before cloning.\n\n"
                f"Tool context is not available. Please ensure you're using this tool within a proper conversation context "
                f"and have configured your repository settings using `set_repository_config()`."
            )
            logger.error("⚠️ No tool context available for repository cloning")
            return f"ERROR: {error_msg}"

        # Determine which repository to clone from
        if user_repo_url and installation_id:
            # Clone from user's repository (with authentication)
            repo_url = await _get_authenticated_repo_url_sync(user_repo_url, installation_id)
            logger.info(f"🔐 Cloning from user's repository: {user_repo_url}")
        else:
            # Fallback: Clone from template repository (for testing or when no user repo configured)
            if language.lower() == "java":
                repo_url = JAVA_TEMPLATE_REPO
            elif language.lower() == "python":
                repo_url = PYTHON_TEMPLATE_REPO
            else:
                return f"ERROR: Unsupported language '{language}'. Supported: java, python"
            logger.warning(f"⚠️ No user repository configured, cloning from template: {repo_url}")

        # Create target directory if not specified - use persistent location
        if target_directory is None:
            # Use /tmp/cyoda_builds/<branch_name> for persistent storage during build
            builds_dir = Path("/tmp/cyoda_builds")
            builds_dir.mkdir(parents=True, exist_ok=True)
            target_directory = str(builds_dir / branch_name)

        target_path = Path(target_directory)

        # Extract repository name and owner from URL for GitHub canvas integration
        # Do this early so we can use it in the early return case
        repository_name = "mcp-cyoda-quart-app"  # Default
        repository_owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")  # Default

        if user_repo_url:
            # Extract owner and repo name from URL (e.g., "https://github.com/owner/repo.git" -> "owner", "repo")
            import re
            # Pattern to match: https://github.com/owner/repo or https://github.com/owner/repo.git
            match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(\.git)?$', user_repo_url)
            if match:
                repository_owner = match.group(1)
                repository_name = match.group(2)
                logger.info(f"📦 Extracted from URL: {repository_owner}/{repository_name}")
            else:
                # Fallback: just extract repo name
                match = re.search(r'/([^/]+?)(\.git)?$', user_repo_url)
                if match:
                    repository_name = match.group(1)
                    logger.info(f"📦 Extracted repository name from URL: {repository_name}")

        # If directory already exists and has .git, assume it's already cloned
        if target_path.exists() and (target_path / ".git").exists():
            logger.info(f"Repository already exists at {target_directory}, skipping clone")
            # Store in context
            if tool_context:
                tool_context.state["repository_path"] = str(target_directory)
                tool_context.state["branch_name"] = branch_name
                tool_context.state["language"] = language
                tool_context.state["repository_name"] = repository_name
                tool_context.state["repository_owner"] = repository_owner
                tool_context.state["repository_url"] = user_repo_url
                tool_context.state["installation_id"] = installation_id
                # Ensure repository_type is preserved (needed for commit_and_push_changes)
                if "repository_type" not in tool_context.state:
                    tool_context.state["repository_type"] = repo_type
            return f"SUCCESS: Repository already exists at {target_directory} on branch {branch_name}"

        target_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Cloning {language} repository from {user_repo_url or 'template'} to {target_directory}"
        )

        # Clone repository
        clone_cmd = ["git", "clone", repo_url, str(target_path)]
        returncode, stdout, stderr = await _run_git_command(clone_cmd, timeout=300)

        if returncode != 0:
            error_msg = stderr or stdout
            logger.error(f"Git clone failed: {error_msg}")
            return f"ERROR: Failed to clone repository: {error_msg}"

        # Handle branch checkout based on use_existing_branch flag
        if use_existing_branch:
            # Checkout existing branch from remote
            logger.info(f"🔄 Checking out existing branch '{branch_name}' from remote...")

            # Fetch all branches from remote
            fetch_cmd = ["git", "fetch", "origin"]
            returncode, stdout, stderr = await _run_git_command(
                fetch_cmd,
                cwd=str(target_path),
                timeout=300,  # 5 minutes for git fetch
            )

            if returncode != 0:
                error_msg = stderr or stdout
                logger.warning(f"Failed to fetch from remote: {error_msg}")

            # Checkout the existing branch
            checkout_cmd = ["git", "checkout", branch_name]
            returncode, stdout, stderr = await _run_git_command(
                checkout_cmd,
                cwd=str(target_path),
                timeout=30,
            )

            if returncode != 0:
                error_msg = stderr or stdout
                logger.error(f"Failed to checkout existing branch '{branch_name}': {error_msg}")
                return f"ERROR: Branch '{branch_name}' does not exist in the repository. Please verify the branch name. Error: {error_msg}"

            # Pull latest changes from remote
            pull_cmd = ["git", "pull", "origin", branch_name]
            returncode, stdout, stderr = await _run_git_command(
                pull_cmd,
                cwd=str(target_path),
                timeout=300,  # 5 minutes for git pull
            )

            if returncode != 0:
                error_msg = stderr or stdout
                logger.warning(f"Failed to pull latest changes: {error_msg}")

            logger.info(f"✅ Successfully checked out existing branch '{branch_name}'")
        else:
            # Create new branch (original behavior)
            # Checkout base branch first (e.g., main)
            checkout_base_cmd = ["git", "checkout", base_branch]
            returncode, stdout, stderr = await _run_git_command(
                checkout_base_cmd,
                cwd=str(target_path),
                timeout=30,
            )

            if returncode != 0:
                error_msg = stderr or stdout
                logger.warning(f"Failed to checkout base branch '{base_branch}': {error_msg}")
                # Continue anyway - might already be on the base branch

            # Create and checkout new branch from base branch
            checkout_cmd = ["git", "checkout", "-b", branch_name]
            returncode, stdout, stderr = await _run_git_command(
                checkout_cmd,
                cwd=str(target_path),
                timeout=30,
            )

            if returncode != 0:
                error_msg = stderr or stdout
                logger.warning(f"Failed to create branch {branch_name}: {error_msg}")
                # Try to checkout existing branch
                checkout_cmd = ["git", "checkout", branch_name]
                returncode, stdout, stderr = await _run_git_command(
                    checkout_cmd,
                    cwd=str(target_path),
                    timeout=30,
                )

        logger.info(
            f"Successfully cloned {language} repository to {target_directory} on branch {branch_name}"
        )

        # Push the new branch to remote immediately (if we have authentication and it's a new branch)
        if not use_existing_branch and user_repo_url and installation_id:
            logger.info(f"🚀 Pushing new branch {branch_name} to {user_repo_url}...")
            push_cmd = ["git", "push", "--set-upstream", "origin", branch_name]
            returncode, stdout, stderr = await _run_git_command(
                push_cmd,
                cwd=str(target_path),
                timeout=300,  # 5 minutes for git push
            )

            if returncode != 0:
                error_msg = stderr or stdout
                logger.warning(f"⚠️ Failed to push branch {branch_name} to remote: {error_msg}")
                # Don't fail the clone operation if push fails - might not have remote configured
            else:
                logger.info(f"✅ Successfully pushed branch {branch_name} to {user_repo_url}")
        elif use_existing_branch:
            logger.info(f"ℹ️ Using existing branch '{branch_name}' - skipping push to remote")
        else:
            logger.warning("⚠️ No user repository URL or installation ID found - skipping push to remote")

        # Store repository path, branch, and repository name in context for later use
        if tool_context:
            tool_context.state["repository_path"] = str(target_directory)
            tool_context.state["branch_name"] = branch_name
            tool_context.state["language"] = language
            tool_context.state["repository_name"] = repository_name
            tool_context.state["repository_owner"] = repository_owner
            tool_context.state["repository_url"] = user_repo_url
            tool_context.state["installation_id"] = installation_id
            tool_context.state["repository_type"] = repo_type

            logger.info(f"✅ Stored in context: repository_path={target_directory}, branch_name={branch_name}, language={language}, repository_name={repository_name}, repository_owner={repository_owner}, repository_url={user_repo_url}, installation_id={installation_id}, repository_type={repo_type}")

            # Update Conversation entity with repository info so commit_and_push_changes can find it
            try:
                conversation_id = tool_context.state.get("conversation_id")
                if conversation_id:
                    from services.services import get_entity_service
                    from application.entity.conversation.version_1.conversation import Conversation

                    entity_service = get_entity_service()
                    response = await entity_service.get_by_id(
                        entity_id=conversation_id,
                        entity_class=Conversation.ENTITY_NAME,
                        entity_version=str(Conversation.ENTITY_VERSION),
                    )

                    if response and response.data:
                        conversation_data = response.data
                        if isinstance(conversation_data, dict):
                            conversation = Conversation(**conversation_data)
                        else:
                            conversation = conversation_data

                        # Update repository fields
                        conversation.repository_name = repository_name
                        conversation.repository_owner = repository_owner
                        conversation.repository_branch = branch_name
                        conversation.repository_url = user_repo_url
                        conversation.installation_id = installation_id

                        # Update conversation entity
                        entity_dict = conversation.model_dump(by_alias=False)
                        await entity_service.update(
                            entity_id=conversation_id,
                            entity=entity_dict,
                            entity_class=Conversation.ENTITY_NAME,
                            entity_version=str(Conversation.ENTITY_VERSION),
                        )
                        logger.info(f"✅ Updated Conversation entity with repository_branch={branch_name}, repository_url={user_repo_url}, installation_id={installation_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update Conversation entity with repository info: {e}", exc_info=True)
                # Don't fail the clone operation if entity update fails

        # Log repository info for debugging
        logger.info(f"📦 Repository info: {repository_owner}/{repository_name}@{branch_name}")

        # Update conversation's workflow_cache with build context
        # This allows setup agent to retrieve language and branch_name when invoked
        try:
            conversation_id = tool_context.state.get("conversation_id") if tool_context else None
            if conversation_id:
                await _update_conversation_build_context(
                    conversation_id=conversation_id,
                    language=language,
                    branch_name=branch_name,
                    repository_name=repository_name
                )
                logger.info(f"✅ Updated conversation workflow_cache with build context for setup agent")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update conversation build context: {e}", exc_info=True)
            # Don't fail the clone operation if context update fails

        # Automatically retrieve and save any files that were attached to the conversation
        # This ensures all files uploaded during the conversation are saved to the branch
        files_saved_message = ""
        if tool_context:
            try:
                logger.info("📂 Checking for conversation files to save to branch...")
                conversation_id = tool_context.state.get("conversation_id")

                if conversation_id:
                    # Get conversation entity to check for files
                    from services.services import get_entity_service
                    from application.entity.conversation.version_1.conversation import Conversation

                    entity_service = get_entity_service()
                    response = await entity_service.get_by_id(
                        entity_id=conversation_id,
                        entity_class=Conversation.ENTITY_NAME,
                        entity_version=str(Conversation.ENTITY_VERSION),
                    )

                    if response and response.data:
                        conversation_data = response.data
                        if isinstance(conversation_data, dict):
                            conversation = Conversation(**conversation_data)
                        else:
                            conversation = conversation_data

                        # Check if there are any files in the conversation
                        has_files = False
                        if hasattr(conversation, 'file_blob_ids') and conversation.file_blob_ids:
                            has_files = True
                            file_count = len(conversation.file_blob_ids)
                            logger.info(f"📎 Found {file_count} files in conversation.file_blob_ids")

                        if has_files:
                            # Call retrieve_and_save_conversation_files to save them
                            logger.info("💾 Automatically saving conversation files to branch...")
                            save_result: str = await retrieve_and_save_conversation_files(tool_context=tool_context)

                            if save_result.startswith("✅"):
                                # Extract file info from result message
                                files_saved_message = f"\n{save_result}"
                                logger.info(f"✅ Conversation files saved successfully")
                            else:
                                logger.warning(f"⚠️ Failed to save conversation files: {save_result}")
                        else:
                            logger.info("📂 No files found in conversation to save")
                else:
                    logger.warning("⚠️ No conversation_id in context, skipping file retrieval")

            except Exception as e:
                logger.warning(f"⚠️ Failed to auto-save conversation files: {e}", exc_info=True)
                # Don't fail the clone operation if file saving fails

        # Return success message for new branches
        # Agent will decide what follow-up options to offer based on context
        if not use_existing_branch:
            # Build GitHub URL
            github_url = f"https://github.com/{repository_owner}/{repository_name}/tree/{branch_name}"
            full_repo_name = f"{repository_owner}/{repository_name}"

            # Return success message without hook
            # Agent will create appropriate follow-up options hook
            success_message = f"✅ Repository configured successfully!\n\n📦 Repository: {full_repo_name}\n🌿 Branch: {branch_name}\n🔗 GitHub URL: {github_url}"
            return success_message

        # Return appropriate success message based on whether it's a new or existing branch
        if use_existing_branch:
            return (
                f"SUCCESS: Repository cloned to {target_directory} and checked out existing branch {branch_name}{files_saved_message}"
            )
        else:
            return (
                f"SUCCESS: Repository cloned to {target_directory} on branch {branch_name}{files_saved_message}"
            )

    except subprocess.TimeoutExpired:
        logger.error("Git operation timed out")
        return "ERROR: Git operation timed out"
    except Exception as e:
        logger.error(f"Failed to clone repository: {e}", exc_info=True)
        return f"ERROR: Failed to clone repository: {str(e)}"


async def generate_application(
    requirements: str,
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    branch_name: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Generate application using Augment CLI with comprehensive prompt.

    Uses repository_path, branch_name, and language from tool_context.state if not provided.
    This allows the agent to call generate_application with just requirements after clone_repository.

    Args:
        requirements: User requirements for the application
        language: Programming language ('java' or 'python') - optional if already in context
        repository_path: Path to cloned repository - optional if already in context
        branch_name: Branch name for the build - optional if already in context
        tool_context: Execution context (auto-injected)

    Returns:
        Status message with build job ID or error
    """
    try:
        # SAFEGUARD: Check if build already started for this branch
        if tool_context:
            existing_build_pid = tool_context.state.get("build_process_pid")
            existing_branch = tool_context.state.get("branch_name")

            if existing_build_pid and existing_branch:
                logger.warning(f"⚠️ Build already started for branch {existing_branch} (PID: {existing_build_pid})")
                return f"⚠️ Build already in progress for branch {existing_branch} (PID: {existing_build_pid}). Please wait for it to complete."

        # Get values from context if not provided
        repository_name = "mcp-cyoda-quart-app"  # Default fallback
        if tool_context:
            language = language or tool_context.state.get("language")
            repository_path = repository_path or tool_context.state.get("repository_path")
            branch_name = branch_name or tool_context.state.get("branch_name")
            repository_name = tool_context.state.get("repository_name", repository_name)

            logger.info(f"🔍 Context state: language={language}, repository_path={repository_path}, branch_name={branch_name}, repository_name={repository_name}")

        # Validate required parameters
        if not language:
            logger.error("Language not specified and not found in context")
            return "ERROR: Language not specified and not found in context. Please call clone_repository first."
        if not repository_path:
            logger.error("Repository path not specified and not found in context")
            return "ERROR: Repository path not specified and not found in context. Please call clone_repository first."
        if not branch_name:
            logger.error("Branch name not specified and not found in context")
            return "ERROR: Branch name not specified and not found in context. Please call clone_repository first."

        # CRITICAL: Validate branch name is not protected
        if await _is_protected_branch(branch_name):
            error_msg = (
                f"🚫 CRITICAL ERROR: Cannot build on protected branch '{branch_name}'. "
                f"Protected branches ({', '.join(sorted(PROTECTED_BRANCHES))}) must NEVER be modified. "
                f"Please use generate_branch_uuid() to create a unique branch name."
            )
            logger.error(error_msg)
            return f"ERROR: {error_msg}"

        # Verify repository directory exists
        repo_path = Path(repository_path)
        if not repo_path.exists():
            logger.error(f"Repository directory does not exist: {repository_path}")
            return f"ERROR: Repository directory does not exist: {repository_path}. Please call clone_repository first."

        if not (repo_path / ".git").exists():
            logger.error(f"Directory exists but is not a git repository: {repository_path}")
            return f"ERROR: Directory exists but is not a git repository: {repository_path}. Please call clone_repository first."

        logger.info(f"✅ Repository verified at: {repository_path}")

        # Load prompt template based on language
        prompt_template = await _load_prompt_template(language)
        if prompt_template.startswith("ERROR"):
            return prompt_template

        # Combine template with user requirements
        full_prompt = f"{prompt_template}\n\n## User Requirements:\n{requirements}"

        # Check if Augment CLI script exists
        script_path = Path(AUGMENT_CLI_SCRIPT)
        if not script_path.exists():
            logger.error(f"Augment CLI script not found: {AUGMENT_CLI_SCRIPT}")
            return f"ERROR: Augment CLI script not found at {AUGMENT_CLI_SCRIPT}"

        logger.info(
            f"Generating {language} application with Augment CLI in {repository_path}"
        )

        # Get Augment model from config
        from common.config.config import AUGMENT_MODEL

        # Call Augment CLI script using asyncio (matching old working code)
        # Format: bash <script> <prompt> <model> <workspace_dir> <branch_id>
        cmd = [
            "bash",
            str(script_path.absolute()),
            full_prompt,
            AUGMENT_MODEL,
            repository_path,
            branch_name,
        ]

        logger.info(f"🔧 Executing command: bash {script_path.name} [prompt] [model] [workspace] [branch]")
        logger.info(f"🎯 Model: {AUGMENT_MODEL}")
        logger.info(f"📁 Workspace: {repository_path}")
        logger.info(f"🌿 Branch: {branch_name}")

        # Start process using asyncio (like old code)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_path.parent),
        )

        logger.info(f"Started Augment CLI process {process.pid}")

        # Check if environment needs deployment and deploy if needed
        env_task_id = None
        conversation_id = tool_context.state.get("conversation_id") if tool_context else None

        if tool_context:
            cyoda_env_deployed = tool_context.state.get("cyoda_env_deployed", False)
            deployment_started = tool_context.state.get("deployment_started", False)

            # If environment is not deployed and deployment hasn't been started yet
            if not cyoda_env_deployed and not deployment_started:
                logger.info("🌍 Environment not deployed - starting deployment in parallel with build")
                try:
                    from application.agents.environment.tools import deploy_cyoda_environment

                    # Deploy environment (this creates a BackgroundTask and starts monitoring)
                    deploy_result = await deploy_cyoda_environment(
                        tool_context=tool_context,
                        build_id=None,
                        env_name=None,
                    )

                    # Extract task_id from result (format: "SUCCESS: ... Task ID: <task_id>)")
                    if "Task ID:" in deploy_result:
                        env_task_id = deploy_result.split("Task ID:")[-1].strip().rstrip(")")
                        logger.info(f"✅ Environment deployment started with task_id: {env_task_id}")
                        tool_context.state["env_deployment_task_id"] = env_task_id
                    else:
                        logger.warning(f"⚠️ Could not extract task_id from deploy result: {deploy_result}")

                except Exception as e:
                    logger.error(f"❌ Failed to deploy environment: {e}", exc_info=True)
                    # Continue with build anyway - environment deployment is not critical for build start

        # Create BackgroundTask entity to track build progress
        build_task_id = None
        if tool_context:
            try:
                from services.services import get_task_service

                task_service = get_task_service()
                user_id = tool_context.state.get("user_id", "unknown")
                repository_type = tool_context.state.get("repository_type", "public")

                # Construct GitHub repository URL
                repository_url = None
                if repository_type == "public":
                    if language.lower() == "python":
                        repo_name = "mcp-cyoda-quart-app"
                    elif language.lower() == "java":
                        repo_name = "java-client-template"
                    else:
                        repo_name = "mcp-cyoda-quart-app"
                    repo_owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")
                    repository_url = f"https://github.com/{repo_owner}/{repo_name}/tree/{branch_name}"

                # Create background task
                background_task = await task_service.create_task(
                    user_id=user_id,
                    task_type="build_app",
                    name=f"Build {language} app on {branch_name}",
                    description=f"Building application: {requirements[:100]}...",
                    branch_name=branch_name,
                    language=language,
                    user_request=requirements,
                    conversation_id=conversation_id,
                    repository_path=repository_path,
                    repository_type=repository_type,
                    repository_url=repository_url,
                )

                build_task_id = background_task.technical_id
                logger.info(f"✅ Created BackgroundTask {build_task_id} for build")

                # Update task to running status
                await task_service.update_task_status(
                    task_id=build_task_id,
                    status="running",
                    message=f"Build started (PID: {process.pid})",
                    progress=5,
                    process_pid=process.pid,
                    build_job_id=f"{language}_{branch_name}_{process.pid}",
                )

                # Store task_id in context
                tool_context.state["background_task_id"] = build_task_id
                tool_context.state["build_process_pid"] = process.pid
                tool_context.state["build_job_id"] = f"{language}_{branch_name}_{process.pid}"

            except Exception as e:
                logger.error(f"Failed to create BackgroundTask: {e}", exc_info=True)
                # Continue anyway - task tracking is not critical for build execution

        # Store build task_id in context for routes to add to conversation
        # Routes will read from tool_context.state and update conversation entity
        if build_task_id and tool_context:
            tool_context.state["build_task_id"] = build_task_id
            logger.info(f"📋 Stored build task {build_task_id} in context for conversation update")

        # Start monitoring in background (don't wait for completion)
        # The monitoring task will update the BackgroundTask entity with progress
        monitoring_task = asyncio.create_task(
            _monitor_build_process(
                process=process,
                repository_path=repository_path,
                branch_name=branch_name,
                timeout_seconds=1800,  # 30 minutes
                tool_context=tool_context,
            )
        )

        # Add task to background tasks set to prevent garbage collection
        from typing import Set, Any
        background_tasks: Set[Any] = getattr(asyncio, '_background_tasks', set())
        if not hasattr(asyncio, '_background_tasks'):
            setattr(asyncio, '_background_tasks', background_tasks)
        background_tasks.add(monitoring_task)
        monitoring_task.add_done_callback(background_tasks.discard)

        logger.info(f"🚀 Started background monitoring task for branch {branch_name}")

        # Return immediately with task_id(s)
        logger.info(f"✅ Build started successfully (PID: {process.pid}, Build Task: {build_task_id}, Env Task: {env_task_id})")

        # Build response with task IDs
        task_ids = []
        if build_task_id:
            task_ids.append(build_task_id)
        if env_task_id:
            task_ids.append(env_task_id)

        if task_ids:
            task_ids_str = ", ".join(task_ids)
            return f"SUCCESS: Build started successfully on branch {branch_name} ({language}). Task IDs: {task_ids_str}. Once the build completes, please call the setup assistant to configure your application."
        else:
            return f"SUCCESS: Build started successfully on branch {branch_name} ({language}). Monitoring build progress in background. Once the build completes, please call the setup assistant to configure your application."

    except Exception as e:
        logger.error(f"Failed to generate application: {e}", exc_info=True)
        return f"ERROR: Failed to generate application: {str(e)}"


async def check_build_status(
    build_job_info: str, tool_context: Optional[ToolContext] = None
) -> str:
    """
    Check the status of a build job.

    Args:
        build_job_info: Build job information (format: "job_id|PID:pid|PATH:path")
        tool_context: Execution context (auto-injected)

    Returns:
        Status message in format "ESCALATE: <message>" or "CONTINUE: <message>"
    """
    try:
        # Parse build job info
        parts = build_job_info.split("|")
        if len(parts) < 3:
            return "ESCALATE: Invalid build job info format"

        job_id = parts[0]
        pid_str = parts[1].replace("PID:", "")
        repo_path = parts[2].replace("PATH:", "")

        pid = int(pid_str)

        # Check if process is still running
        try:
            os.kill(pid, 0)  # Signal 0 checks if process exists
            # Process is still running
            logger.info(f"Build job {job_id} (PID: {pid}) is still running")

            # Status is tracked in BackgroundTask entity only
            # No need to send messages to conversation

            return f"CONTINUE: Build job {job_id} is still in progress"
        except OSError:
            # Process has finished
            logger.info(f"Build job {job_id} (PID: {pid}) has completed")

            # Check for build artifacts or success indicators
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                # Status is tracked in BackgroundTask entity only
                return f"ESCALATE: Build completed but repository path {repo_path} not found"

            # Check for common build success indicators
            success_indicators = [
                repo_path_obj / "build" / "libs",  # Java Gradle
                repo_path_obj / "target",  # Java Maven
                repo_path_obj / ".venv",  # Python venv
                repo_path_obj / "dist",  # Python dist
            ]

            has_artifacts = any(indicator.exists() for indicator in success_indicators)

            if has_artifacts:
                # Status is tracked in BackgroundTask entity only
                return f"ESCALATE: Build job {job_id} completed successfully. Artifacts found in {repo_path}"
            else:
                # Status is tracked in BackgroundTask entity only
                return f"ESCALATE: Build job {job_id} completed. Please verify build output in {repo_path}"

    except ValueError:
        logger.error(f"Invalid PID in build job info: {build_job_info}")
        return "ESCALATE: Invalid build job info - could not parse PID"
    except Exception as e:
        logger.error(f"Failed to check build status: {e}", exc_info=True)
        return f"ESCALATE: Error checking build status: {str(e)}"


async def wait_before_next_check(seconds: int = 30) -> str:
    """
    Wait before checking build status again.

    Args:
        seconds: Number of seconds to wait (default: 30)

    Returns:
        Confirmation message
    """
    logger.info(f"Waiting {seconds} seconds before next build status check")
    await asyncio.sleep(seconds)
    return f"Waited {seconds} seconds. Ready for next status check."


async def _stream_process_output(
    process: Any,
    task_id: Optional[str] = None,
) -> None:
    """
    Stream process output chunks as they arrive.
    Reads from stdout and stderr, updates BackgroundTask with output.

    Args:
        process: The asyncio subprocess
        task_id: BackgroundTask ID for storing output
    """
    try:
        from services.services import get_task_service

        task_service = get_task_service()
        accumulated_output = []
        chunk_size = 1024  # Read 1KB at a time
        last_update_time = asyncio.get_event_loop().time()
        update_interval = 2  # Update every 2 seconds or 5KB

        while True:
            try:
                # Read from stdout with timeout
                chunk = await asyncio.wait_for(
                    process.stdout.read(chunk_size),
                    timeout=0.5
                )
                if chunk:
                    output_str = chunk.decode('utf-8', errors='replace')
                    accumulated_output.append(output_str)
                    logger.debug(f"📤 Output chunk: {output_str[:100]}...")

                    current_time = asyncio.get_event_loop().time()
                    accumulated_size = sum(len(s) for s in accumulated_output)

                    # Update task with accumulated output every 5KB or every 2 seconds
                    if (accumulated_size > 5120 or (current_time - last_update_time) > update_interval) and task_id:
                        try:
                            full_output = ''.join(accumulated_output)
                            # Get current task to preserve existing metadata
                            current_task = await task_service.get_task(task_id)
                            existing_metadata = current_task.metadata if current_task else {}

                            # Merge existing metadata with new output
                            updated_metadata = {**existing_metadata, "output": full_output[-10000:]}  # Keep last 10KB

                            await task_service.update_task_status(
                                task_id=task_id,
                                metadata=updated_metadata,
                            )
                            logger.info(f"📤 Updated task {task_id} with {accumulated_size} bytes of output")
                            accumulated_output = []
                            last_update_time = current_time
                        except Exception as e:
                            logger.debug(f"Could not update task output: {e}")
                else:
                    # EOF reached
                    break
            except asyncio.TimeoutError:
                # No data available, check if we should update anyway
                current_time = asyncio.get_event_loop().time()
                if accumulated_output and (current_time - last_update_time) > update_interval and task_id:
                    try:
                        full_output = ''.join(accumulated_output)
                        current_task = await task_service.get_task(task_id)
                        existing_metadata = current_task.metadata if current_task else {}
                        updated_metadata = {**existing_metadata, "output": full_output[-10000:]}
                        await task_service.update_task_status(
                            task_id=task_id,
                            metadata=updated_metadata,
                        )
                        logger.debug(f"📤 Periodic output update: {len(full_output)} characters")
                        accumulated_output = []
                        last_update_time = current_time
                    except Exception as e:
                        logger.debug(f"Could not update task output: {e}")
            except Exception as e:
                logger.debug(f"Error reading stdout: {e}")
                break

        # Update task with any remaining output when process completes
        if accumulated_output and task_id:
            try:
                full_output = ''.join(accumulated_output)
                # Get current task to preserve existing metadata
                current_task = await task_service.get_task(task_id)
                existing_metadata = current_task.metadata if current_task else {}

                # Merge existing metadata with final output
                updated_metadata = {**existing_metadata, "output": full_output[-10000:]}  # Keep last 10KB

                await task_service.update_task_status(
                    task_id=task_id,
                    metadata=updated_metadata,
                )
                logger.info(f"📤 Final output update: {len(full_output)} characters")
            except Exception as e:
                logger.debug(f"Could not update final task output: {e}")

    except Exception as e:
        logger.warning(f"Error streaming process output: {e}")


async def _monitor_build_process(
    process: Any,
    repository_path: str,
    branch_name: str,
    timeout_seconds: int = 1800,
    tool_context: Optional[ToolContext] = None,
) -> None:
    """
    Monitor build process with periodic checks and git commits.
    Updates BackgroundTask entity every 30 seconds with progress.
    Streams output chunks as they arrive.

    Args:
        process: The asyncio subprocess
        repository_path: Path to repository
        branch_name: Branch name
        timeout_seconds: Maximum time to wait before terminating
        tool_context: Tool context for conversation and task updates
    """
    check_interval = 10  # Check every 10 seconds for faster completion detection
    elapsed_time = 0
    pid = process.pid

    logger.info(f"🔍 [{branch_name}] Monitoring task started for PID {pid}")
    logger.info(f"🔍 [{branch_name}] tool_context: {tool_context is not None}")
    logger.info(f"🔍 [{branch_name}] conversation_id: {tool_context.state.get('conversation_id') if tool_context else 'N/A'}")

    # Get task_id from context
    task_id = tool_context.state.get("background_task_id") if tool_context else None
    logger.info(f"🔍 [{branch_name}] background_task_id: {task_id}")

    # Start streaming output in background
    output_stream_task = asyncio.create_task(
        _stream_process_output(process=process, task_id=task_id)
    )
    logger.info(f"📤 Started output streaming for PID {pid}")

    # Send initial notification immediately when process starts
    if tool_context:
        try:
            logger.info(f"🔍 [{branch_name}] Sending initial notification...")

            # Commit and push initial state
            commit_result = await _commit_and_push_changes(
                repository_path=repository_path,
                branch_name=branch_name,
            )

            logger.info(f"🔍 [{branch_name}] Commit result: {commit_result.get('status', 'unknown')}")

            # Progress updates are now tracked in BackgroundTask entity only
            # No need to send notifications to conversation
            logger.info(f"✅ [{branch_name}] Initial commit completed - progress tracked in BackgroundTask")
        except Exception as e:
            logger.error(f"❌ [{branch_name}] Failed to send initial notification: {e}", exc_info=True)

    while elapsed_time < timeout_seconds:
        try:
            # Wait for either process completion or check interval
            remaining_time = min(check_interval, timeout_seconds - elapsed_time)
            await asyncio.wait_for(process.wait(), timeout=remaining_time)
            # Process completed normally
            logger.info(f"✅ Process {pid} completed normally")

            # Update BackgroundTask to completed
            if task_id:
                try:
                    from services.services import get_task_service

                    task_service = get_task_service()
                    await task_service.update_task_status(
                        task_id=task_id,
                        status="completed",
                        message="Build completed successfully - ready for setup",
                        progress=100,
                    )
                    logger.info(f"✅ Updated BackgroundTask {task_id} to completed")

                    # Update conversation metadata to indicate build completion
                    conversation_id = tool_context.state.get("conversation_id") if tool_context else None
                    language = tool_context.state.get("language") if tool_context else None

                    if conversation_id and language:
                        try:
                            from services.services import get_entity_service
                            from application.entity.conversation.version_1.conversation import Conversation

                            entity_service = get_entity_service()

                            # Get conversation
                            response = await entity_service.get_by_id(
                                entity_id=conversation_id,
                                entity_class=Conversation.ENTITY_NAME,
                                entity_version=str(Conversation.ENTITY_VERSION),
                            )

                            if response and response.data:
                                conversation_data = response.data if isinstance(response.data, dict) else response.data.model_dump(by_alias=False)
                                conversation = Conversation(**conversation_data)

                                # Ensure metadata is initialized
                                if conversation.metadata is None:
                                    conversation.metadata = {}

                                # Add build completion metadata
                                conversation.metadata["build_completed"] = True
                                conversation.metadata["build_branch"] = branch_name
                                conversation.metadata["build_language"] = language
                                conversation.metadata["build_task_id"] = task_id

                                # Update conversation
                                entity_dict = conversation.model_dump(by_alias=False)
                                await entity_service.update(
                                    entity_id=conversation_id,
                                    entity=entity_dict,
                                    entity_class=Conversation.ENTITY_NAME,
                                    entity_version=str(Conversation.ENTITY_VERSION),
                                )
                                logger.info(f"✅ Updated conversation {conversation_id} with build completion metadata")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to update conversation metadata: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update BackgroundTask: {e}")

            # Build completion is tracked in BackgroundTask entity only
            # No need to send messages to conversation anymore
            logger.info("✅ Build completed - status tracked in BackgroundTask entity")

            return
        except asyncio.TimeoutError:
            # Manually check if process is still running by PID
            if not await _is_process_running(pid):
                # Process has exited silently
                logger.info(f"✅ Process {pid} completed (detected during PID check)")

                # Update BackgroundTask to completed
                if task_id:
                    try:
                        from services.services import get_task_service

                        task_service = get_task_service()
                        await task_service.update_task_status(
                            task_id=task_id,
                            status="completed",
                            message="Build completed successfully - ready for setup",
                            progress=100,
                        )
                        logger.info(f"✅ Updated BackgroundTask {task_id} to completed")

                        # Update conversation metadata to indicate build completion
                        conversation_id = tool_context.state.get("conversation_id") if tool_context else None
                        language = tool_context.state.get("language") if tool_context else None

                        if conversation_id and language:
                            try:
                                from services.services import get_entity_service
                                from application.entity.conversation.version_1.conversation import Conversation

                                entity_service = get_entity_service()

                                # Get conversation
                                response = await entity_service.get_by_id(
                                    entity_id=conversation_id,
                                    entity_class=Conversation.ENTITY_NAME,
                                    entity_version=str(Conversation.ENTITY_VERSION),
                                )

                                if response and response.data:
                                    conversation_data = response.data if isinstance(response.data, dict) else response.data.model_dump(by_alias=False)
                                    conversation = Conversation(**conversation_data)

                                    # Ensure metadata is initialized
                                    if conversation.metadata is None:
                                        conversation.metadata = {}

                                    # Add build completion metadata
                                    conversation.metadata["build_completed"] = True
                                    conversation.metadata["build_branch"] = branch_name
                                    conversation.metadata["build_language"] = language
                                    conversation.metadata["build_task_id"] = task_id

                                    # Update conversation
                                    entity_dict = conversation.model_dump(by_alias=False)
                                    await entity_service.update(
                                        entity_id=conversation_id,
                                        entity=entity_dict,
                                        entity_class=Conversation.ENTITY_NAME,
                                        entity_version=str(Conversation.ENTITY_VERSION),
                                    )
                                    logger.info(f"✅ Updated conversation {conversation_id} with build completion metadata")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to update conversation metadata: {e}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to update BackgroundTask: {e}")

                # Build completion is tracked in BackgroundTask entity only
                # No need to send messages to conversation anymore
                logger.info("✅ Build completed - status tracked in BackgroundTask entity")

                return

            elapsed_time += remaining_time
            logger.debug(
                f"🔍 Process {pid} still running after {elapsed_time}s (timeout: {timeout_seconds}s)"
            )

            # Update BackgroundTask every 30 seconds
            if task_id and elapsed_time % 30 == 0:
                try:
                    from services.services import get_task_service

                    task_service = get_task_service()
                    # Calculate progress (0-95%, reserve 95-100 for completion)
                    progress = min(95, int((elapsed_time / timeout_seconds) * 95))
                    await task_service.add_progress_update(
                        task_id=task_id,
                        message=f"Build in progress... ({elapsed_time}s elapsed)",
                        progress=progress,
                        metadata={"elapsed_time": elapsed_time, "pid": pid},
                    )
                    logger.info(f"📊 Updated BackgroundTask {task_id} progress: {progress}%")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update BackgroundTask progress: {e}")

            # Commit and push changes, then send progress update every 60 seconds
            # (but check for completion every 10 seconds)
            if tool_context and elapsed_time % 60 == 0:
                try:
                    # Commit and push changes
                    commit_result = await _commit_and_push_changes(
                        repository_path=repository_path,
                        branch_name=branch_name,
                    )

                    # Progress updates are now tracked in BackgroundTask entity only
                    logger.info(f"✅ [{branch_name}] Progress commit completed - tracked in BackgroundTask")
                except Exception as e:
                    logger.warning(
                        f"⚠️ [{branch_name}] Failed to commit/push: {e}"
                    )

    # Timeout exceeded, terminate the process
    logger.error(f"⏰ Process exceeded {timeout_seconds} seconds, terminating... (PID: {pid})")

    # Update BackgroundTask to failed
    if task_id:
        try:
            from services.services import get_task_service

            task_service = get_task_service()
            await task_service.update_task_status(
                task_id=task_id,
                status="failed",
                message=f"Build timeout after {timeout_seconds} seconds",
                progress=0,
                error=f"Process exceeded {timeout_seconds} seconds timeout",
            )
            logger.info(f"❌ Updated BackgroundTask {task_id} to failed (timeout)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update BackgroundTask on timeout: {e}")

    await _terminate_process(process)


async def _terminate_process(process: Any) -> None:
    """
    Terminate a process gracefully, then forcefully if needed.

    Args:
        process: The asyncio subprocess to terminate
    """
    kill_grace_seconds = 5
    try:
        process.terminate()
    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(process.wait(), timeout=kill_grace_seconds)
    except asyncio.TimeoutError:
        logger.error(f"⚠️ Process did not terminate, killing... (PID: {process.pid})")
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()


async def _is_process_running(pid: int) -> bool:
    """
    Check if a process is still running by PID.

    Args:
        pid: Process ID to check

    Returns:
        True if process is running, False otherwise
    """
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


async def _commit_and_push_changes(
    repository_path: str, branch_name: str
) -> Dict[str, Any]:
    """
    Commit and push all changes in the repository.
    Based on old working code from auggie_processor.py.

    Args:
        repository_path: Path to repository
        branch_name: Branch name

    Returns:
        Dict with success status, whether there were changes, and git diff
    """
    try:
        # Add all changes
        logger.debug(f"📦 [{branch_name}] Adding all changes to git...")
        process = await asyncio.create_subprocess_exec(
            "git",
            "add",
            ".",
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(
                f"❌ [{branch_name}] Git add failed: {stderr.decode('utf-8')}"
            )
            return {"success": False, "had_changes": False, "diff": ""}

        # Check if there are changes to commit
        logger.debug(f"🔍 [{branch_name}] Checking for changes to commit...")
        process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--cached",
            "--quiet",
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

        # If return code is 0, there are no changes to commit
        if process.returncode == 0:
            logger.info(f"ℹ️ [{branch_name}] No changes to commit")
            return {"success": True, "had_changes": False, "diff": ""}

        # Get git diff stats before committing
        process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--cached",
            "--stat",
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        diff_stdout, diff_stderr = await process.communicate()
        git_diff = diff_stdout.decode("utf-8", errors="replace") if diff_stdout else ""

        # Commit changes
        commit_message = f"Generated code using Augment CLI - {branch_name}"
        logger.debug(f"💾 [{branch_name}] Committing changes...")
        process = await asyncio.create_subprocess_exec(
            "git",
            "commit",
            "-m",
            commit_message,
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(
                f"❌ [{branch_name}] Git commit failed: {stderr.decode('utf-8')}"
            )
            return {"success": False, "had_changes": True, "diff": git_diff}

        logger.info(f"✅ [{branch_name}] Changes committed successfully")

        # Push changes with --set-upstream for new branches
        logger.debug(f"🚀 [{branch_name}] Pushing changes to remote...")
        process = await asyncio.create_subprocess_exec(
            "git",
            "push",
            "--set-upstream",
            "origin",
            branch_name,
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.warning(
                f"⚠️ [{branch_name}] Git push failed (may not have remote): {stderr.decode('utf-8')}"
            )
            # Don't fail if push fails - might not have remote configured
            return {"success": True, "had_changes": True, "diff": git_diff}

        logger.info(
            f"🎉 [{branch_name}] Successfully committed and pushed changes to origin/{branch_name}"
        )
        return {"success": True, "had_changes": True, "diff": git_diff}

    except Exception as e:
        logger.exception(f"Error committing changes: {e}")
        return {"success": False, "had_changes": False, "diff": ""}


async def _get_git_diff(repository_path: str) -> str:
    """
    Get git diff stats for the repository.

    Args:
        repository_path: Path to repository

    Returns:
        Git diff output or empty string
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--stat",
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return stdout.decode("utf-8", errors="replace") if stdout else ""
        else:
            return ""
    except Exception as e:
        logger.warning(f"Failed to get git diff: {e}")
        return ""


# Progress notifications are now handled entirely by BackgroundTask entity
# No need to send messages to conversation anymore


async def retrieve_and_save_conversation_files(
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Retrieve files attached to the conversation and save them to the branch.

    This tool is used when files were attached at the start of the conversation
    (before the branch was created). It retrieves files from the Conversation entity
    and saves them to the functional requirements directory.

    Args:
        tool_context: Execution context (auto-injected)

    Returns:
        Status message indicating success or error
    """
    try:
        if not tool_context:
            return "ERROR: tool_context not available"

        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return "ERROR: conversation_id not found in context"

        logger.info(f"📂 Retrieving files from conversation {conversation_id}")

        # Get conversation entity
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response:
            return f"ERROR: Conversation {conversation_id} not found"

        conversation_data = response.data
        if isinstance(conversation_data, dict):
            conversation = Conversation(**conversation_data)
        else:
            conversation = conversation_data

        # Collect file IDs from conversation
        file_ids: list[str] = []

        # 1. Check conversation-level file_blob_ids (primary source - contains all files)
        if hasattr(conversation, 'file_blob_ids') and conversation.file_blob_ids:
            file_ids.extend(conversation.file_blob_ids)
            logger.info(f"📎 Found {len(conversation.file_blob_ids)} files in conversation.file_blob_ids")
        else:
            # 2. Fallback: Check chat_flow.finished_flow for file attachments (legacy/backward compatibility)
            logger.info("📎 No conversation-level file_blob_ids, scanning messages...")
            if hasattr(conversation, 'chat_flow') and conversation.chat_flow and conversation.chat_flow.get("finished_flow"):
                for message in conversation.chat_flow["finished_flow"]:
                    if isinstance(message, dict) and message.get("file_blob_ids"):
                        file_ids.extend(message["file_blob_ids"])
                        logger.info(f"📎 Found {len(message['file_blob_ids'])} files in message {message.get('technical_id')}")

        # Remove duplicates (in case of legacy data with duplicates)
        file_ids = list(dict.fromkeys(file_ids))  # Preserves order while removing duplicates

        if not file_ids:
            logger.warning("⚠️ No files found in conversation entity")
            logger.info(f"Conversation data: file_blob_ids={getattr(conversation, 'file_blob_ids', None)}")
            if hasattr(conversation, 'chat_flow'):
                logger.info(f"Chat flow: {conversation.chat_flow}")
            return "No files found in conversation. If you attached a file, it may not have been saved to the conversation entity yet. Please try providing the file content directly, or check if the file was successfully uploaded."

        logger.info(f"📂 Total unique files to retrieve: {len(file_ids)}: {file_ids}")

        # Retrieve and decode files from edge messages
        files_to_save: list[dict[str, str]] = []
        for file_id in file_ids:
            try:
                # Retrieve edge message using repository directly
                # Edge messages require special meta parameter that get_by_id() doesn't support
                from common.config.config import CYODA_ENTITY_TYPE_EDGE_MESSAGE
                from services.services import get_repository

                logger.info(f"🔍 Retrieving edge message: {file_id}")

                # Get repository and call find_by_id with edge message meta
                repository = get_repository()
                meta = {"type": CYODA_ENTITY_TYPE_EDGE_MESSAGE}

                edge_data = await repository.find_by_id(
                    meta=meta,
                    entity_id=file_id
                )

                if not edge_data:
                    logger.warning(f"⚠️ Edge message {file_id} not found")
                    continue

                if not edge_data:
                    logger.warning(f"⚠️ Edge message {file_id} returned empty data")
                    continue

                logger.info(f"📥 Retrieved edge message {file_id}: {type(edge_data)}, keys: {edge_data.keys() if isinstance(edge_data, dict) else 'N/A'}")

                filename = f"file_{len(files_to_save) + 1}.txt"
                file_content = ""

                if isinstance(edge_data, dict):
                    # Get metadata for filename
                    metadata = edge_data.get('metadata', {})
                    if metadata and 'filename' in metadata:
                        filename = metadata['filename']

                    # Get base64 content
                    base64_content = edge_data.get('message', '')

                    # Decode if base64
                    if base64_content and metadata.get('encoding') == 'base64':
                        try:
                            import base64
                            file_content = base64.b64decode(base64_content).decode('utf-8')
                            logger.info(f"✅ Decoded file: {filename} ({len(file_content)} chars)")
                        except Exception as e:
                            logger.error(f"❌ Failed to decode {filename}: {e}")
                            file_content = str(base64_content)
                    else:
                        file_content = str(base64_content)
                elif hasattr(edge_data, 'message') and hasattr(edge_data, 'metadata'):
                    # Handle object format
                    base64_content = edge_data.message
                    metadata = edge_data.metadata or {}

                    if metadata.get('filename'):
                        filename = metadata['filename']

                    if base64_content and metadata.get('encoding') == 'base64':
                        try:
                            import base64
                            file_content = base64.b64decode(base64_content).decode('utf-8')
                            logger.info(f"✅ Decoded file: {filename} ({len(file_content)} chars)")
                        except Exception as e:
                            logger.error(f"❌ Failed to decode {filename}: {e}")
                            file_content = str(base64_content)
                    else:
                        file_content = str(base64_content)
                else:
                    # Fallback for unexpected format
                    file_content = str(edge_data)

                files_to_save.append({"filename": filename, "content": file_content})
                logger.info(f"📎 Added file to save list: {filename}")

            except Exception as e:
                logger.error(f"❌ Failed to retrieve file {file_id}: {e}", exc_info=True)
                continue

        if not files_to_save:
            return "ERROR: No valid files could be retrieved from conversation"

        # Save files to branch using existing tool
        logger.info(f"💾 Saving {len(files_to_save)} files to branch...")
        return await save_files_to_branch(files=files_to_save, tool_context=tool_context)

    except Exception as e:
        logger.error(f"Failed to retrieve and save conversation files: {e}", exc_info=True)
        return f"ERROR: Failed to retrieve and save conversation files: {str(e)}"


async def save_files_to_branch(
    files: list[dict[str, str]],
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Save user-provided files to the functional requirements directory in the repository.

    Files are saved to:
    - Java: src/main/resources/functional_requirements/
    - Python: application/resources/functional_requirements/

    After saving files, they are committed and pushed to the branch.

    Args:
        files: List of file dictionaries with 'filename' and 'content' keys
               Example: [{"filename": "api_spec.yaml", "content": "openapi: 3.0.0..."}]
        tool_context: Execution context (auto-injected)

    Returns:
        Status message indicating success or error
    """
    try:
        # Get repository info from context
        if not tool_context:
            return "ERROR: tool_context not available"

        repository_path = tool_context.state.get("repository_path")
        branch_name = tool_context.state.get("branch_name")
        language = tool_context.state.get("language")
        repository_type = tool_context.state.get("repository_type")
        user_repository_url = tool_context.state.get("user_repository_url")
        installation_id = tool_context.state.get("installation_id")

        # Require explicit repository type configuration
        if repository_type is None:
            error_msg = (
                f"❌ Repository type not configured.\n\n"
                f"This usually means the repository was not properly cloned with `clone_repository()` "
                f"or the repository configuration was not set with `set_repository_config()`.\n\n"
                f"Please ensure you have called `set_repository_config()` with either:\n"
                f"- `repository_type='public'` for Cyoda public repositories\n"
                f"- `repository_type='private'` with your installation_id and repository_url"
            )
            logger.error("⚠️ No repository type found in context for commit/push operation")
            return f"ERROR: {error_msg}"

        if not repository_path:
            return "ERROR: Repository path not found in context. Please call clone_repository first."
        if not branch_name:
            return "ERROR: Branch name not found in context. Please call clone_repository first."
        if not language:
            return "ERROR: Language not found in context. Please call clone_repository first."

        # Validate repository exists
        repo_path = Path(repository_path)
        if not repo_path.exists():
            return f"ERROR: Repository directory does not exist: {repository_path}"

        # Determine functional requirements directory based on language
        if language.lower() == "java":
            func_req_dir = repo_path / "src" / "main" / "resources" / "functional_requirements"
        elif language.lower() == "python":
            func_req_dir = repo_path / "application" / "resources" / "functional_requirements"
        else:
            return f"ERROR: Unsupported language '{language}'. Supported: java, python"

        # Create functional requirements directory if it doesn't exist
        func_req_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created/verified functional requirements directory: {func_req_dir}")

        # Save each file
        saved_files = []
        for file_info in files:
            if not isinstance(file_info, dict):
                logger.warning(f"⚠️ Skipping invalid file info (not a dict): {file_info}")
                continue

            filename = file_info.get("filename")
            content = file_info.get("content")

            if not filename or not content:
                logger.warning(f"⚠️ Skipping file with missing filename or content: {file_info}")
                continue

            # Sanitize filename (prevent directory traversal)
            filename = Path(filename).name  # Get just the filename, no path components

            file_path = func_req_dir / filename

            # Write file
            try:
                file_path.write_text(content, encoding="utf-8")
                saved_files.append(filename)
                logger.info(f"✅ Saved file: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to save file {filename}: {e}")
                return f"ERROR: Failed to save file {filename}: {str(e)}"

        if not saved_files:
            return "ERROR: No valid files were provided to save"

        # Commit and push the files
        logger.info(f"📦 Committing and pushing {len(saved_files)} files to branch {branch_name}...")

        try:
            # Add files to git
            process = await asyncio.create_subprocess_exec(
                "git",
                "add",
                str(func_req_dir),
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                logger.error(f"❌ Git add failed: {error_msg}")
                return f"ERROR: Failed to add files to git: {error_msg}"

            # Commit files
            commit_message = f"Add functional requirements files: {', '.join(saved_files)}"
            process = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                commit_message,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                # Check if there were no changes to commit
                error_msg = stderr.decode("utf-8") if stderr else ""
                if "nothing to commit" in error_msg.lower():
                    logger.info("ℹ️ Files already committed (no changes)")
                else:
                    logger.error(f"❌ Git commit failed: {error_msg}")
                    return f"ERROR: Failed to commit files: {error_msg}"

            # Update remote URL with fresh authentication token before pushing
            # This is critical because GitHub App tokens expire after 1 hour
            if repository_type in ["public", "private"]:
                # Determine the repository URL to use
                if repository_type == "private" and user_repository_url and installation_id:
                    repo_url_to_use = user_repository_url
                    installation_id_to_use = installation_id
                    logger.info(f"🔐 Refreshing authentication for private repository: {repo_url_to_use}")
                elif repository_type == "public":
                    # For public repos, use the configured public repository URL from .env
                    if language.lower() == "python":
                        repo_url_to_use = PYTHON_PUBLIC_REPO_URL
                    elif language.lower() == "java":
                        repo_url_to_use = JAVA_PUBLIC_REPO_URL
                    else:
                        repo_url_to_use = None
                    installation_id_to_use = GITHUB_PUBLIC_REPO_INSTALLATION_ID
                    logger.info(f"🔐 Refreshing authentication for public repository: {repo_url_to_use}")
                else:
                    repo_url_to_use = None
                    installation_id_to_use = None

                # Update the remote URL with fresh authentication
                if repo_url_to_use and installation_id_to_use:
                    try:
                        authenticated_url = await _get_authenticated_repo_url_sync(repo_url_to_use, installation_id_to_use)

                        # Update the origin remote URL
                        set_url_process = await asyncio.create_subprocess_exec(
                            "git",
                            "remote",
                            "set-url",
                            "origin",
                            authenticated_url,
                            cwd=str(repo_path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        stdout, stderr = await set_url_process.communicate()

                        if set_url_process.returncode != 0:
                            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                            logger.warning(f"⚠️ Failed to update remote URL: {error_msg}")
                        else:
                            logger.info(f"✅ Successfully refreshed remote authentication")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to refresh authentication: {e}")

            # Push to remote
            process = await asyncio.create_subprocess_exec(
                "git",
                "push",
                "--set-upstream",
                "origin",
                branch_name,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                logger.warning(f"⚠️ Git push failed (may not have remote): {error_msg}")
                # Don't fail if push fails - might not have remote configured
                return f"SUCCESS: Saved {len(saved_files)} file(s) to {func_req_dir.relative_to(repo_path)} and committed locally. Push to remote failed (may not have remote configured)."

            logger.info(f"🎉 Successfully saved, committed, and pushed {len(saved_files)} files")

            return f"SUCCESS: Saved {len(saved_files)} file(s) to {func_req_dir.relative_to(repo_path)}, committed, and pushed to branch {branch_name}. Files: {', '.join(saved_files)}"

        except Exception as e:
            logger.error(f"❌ Failed to commit/push files: {e}", exc_info=True)
            return f"ERROR: Files were saved but failed to commit/push: {str(e)}"

    except Exception as e:
        logger.error(f"Failed to save files to branch: {e}", exc_info=True)
        return f"ERROR: Failed to save files to branch: {str(e)}"


async def _load_prompt_template(language: str) -> str:
    """
    Load prompt template for the specified language.

    Args:
        language: Programming language ('java' or 'python')

    Returns:
        Prompt template content or error message
    """
    try:
        # Use the load_template utility from prompts module
        template_name = f"build_{language.lower()}_instructions"
        content = load_template(template_name)

        logger.info(f"Loaded prompt template for {language} ({len(content)} chars)")
        return content

    except FileNotFoundError as e:
        logger.error(f"Prompt template not found: {e}")
        return f"ERROR: Prompt template not found for language '{language}'"
    except Exception as e:
        logger.error(f"Failed to load prompt template: {e}", exc_info=True)
        return f"ERROR: Failed to load prompt template: {str(e)}"
