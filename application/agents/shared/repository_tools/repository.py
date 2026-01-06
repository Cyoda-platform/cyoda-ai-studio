"""
Repository management functions for cloning, configuring, and managing Git repositories.

This module handles repository operations including:
- Branch UUID generation
- Repository configuration checks
- Repository cloning with branch management
- Repository configuration setting

Internal organization:
- core/config.py: Configuration & validation
- core/errors.py: Error builders
- core/git_ops.py: Git operations
- core/context.py: Context & entity updates
- core/handlers.py: Internal handler functions
"""

import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.constants import (
    GITHUB_PUBLIC_REPO_INSTALLATION_ID,
    JAVA_PUBLIC_REPO_URL,
    PYTHON_PUBLIC_REPO_URL,
)
from application.agents.shared.repository_tools.git_operations import (
    _run_git_command,
    _get_authenticated_repo_url_sync,
)
from services.services import get_entity_service
# Re-export from core modules for backward compatibility
from .core import (
    BranchConfiguration,
    _validate_tool_context,
    _extract_config_from_tool_state,
    _extract_config_from_conversation,
    _detect_language,
    _determine_repository_type,
    _get_private_repo_config,
    _get_public_repo_config,
    _build_missing_context_error,
    _build_no_config_error,
    _build_invalid_repo_type_error,
    _get_repository_config_from_context,
    _clone_repo_to_path,
    _checkout_existing_branch,
    _create_new_branch,
    _push_branch_to_remote,
    _store_in_tool_context,
    _update_conversation_entity,
    _update_conversation_build_context_wrapper,
    _handle_already_cloned_repo,
    _handle_new_branch,
    _handle_existing_branch,
    _build_target_path,
    _determine_repo_url,
    _validate_and_check_protected_branch,
    _extract_repo_name_and_owner,
    _setup_repository_clone,
    _handle_branch_setup,
    _finalize_clone,
    _format_clone_success_message,
    _perform_clone_and_branch,
    _handle_push_and_finalize,
)

logger = logging.getLogger(__name__)


async def generate_branch_uuid() -> str:
    """Generate a UUID-based branch name for public repositories.

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
    """Check if a branch is already configured in the current conversation.

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
        # Step 1: Validate tool context
        is_valid, error_msg, conversation_id = _validate_tool_context(tool_context)
        if not is_valid:
            return BranchConfiguration(configured=False, error=error_msg).model_dump_json()

        # Step 2: Extract configuration from tool context state (most up-to-date source)
        config = _extract_config_from_tool_state(tool_context)

        # Step 3: Fall back to conversation entity if needed
        if not config["repository_name"] or not config["repository_branch"]:
            success, error_msg, config = await _extract_config_from_conversation(
                conversation_id, config
            )
            if not success:
                return BranchConfiguration(configured=False, error=error_msg).model_dump_json()

        # Step 4: Check if branch is configured
        repository_name = config.get("repository_name")
        repository_branch = config.get("repository_branch")

        if not repository_name or not repository_branch:
            return BranchConfiguration(
                configured=False,
                message="No branch configuration found in conversation"
            ).model_dump_json()

        # Step 5: Determine language and repository type
        language = _detect_language(repository_name)
        repository_type = _determine_repository_type(
            config.get("repository_url"), config.get("installation_id")
        )

        logger.info(
            f"✅ Found existing branch configuration: "
            f"{config.get('repository_owner')}/{repository_name}@{repository_branch}"
        )

        # Step 6: Build and return configuration
        result = BranchConfiguration(
            configured=True,
            language=language,
            repository_type=repository_type,
            repository_name=repository_name,
            repository_owner=config.get("repository_owner"),
            repository_branch=repository_branch,
            repository_url=config.get("repository_url"),
            installation_id=config.get("installation_id"),
            repository_path=config.get("repository_path"),
            ready_to_build=bool(config.get("repository_path")),
        )

        return result.model_dump_json()

    except Exception as e:
        logger.error(f"Error checking existing branch configuration: {e}", exc_info=True)
        return BranchConfiguration(configured=False, error=str(e)).model_dump_json()


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
    if not repository_type:
        raise ValueError("repository_type parameter is required and cannot be empty")

    if repository_type not in ["public", "private"]:
        raise ValueError(
            f"repository_type must be 'public' or 'private', got '{repository_type}'"
        )

    if not tool_context:
        raise ValueError("Tool context not available. This function must be called within a conversation context.")

    tool_context.state["repository_type"] = repository_type

    if repository_type == "private":
        if not installation_id:
            raise ValueError(
                "installation_id parameter is required for private repositories"
            )
        if not repository_url:
            raise ValueError(
                "repository_url parameter is required for private repositories"
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


async def clone_repository(
    language: str,
    branch_name: str,
    target_directory: Optional[str] = None,
    use_existing_branch: bool = False,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Clone repository based on language and create/checkout branch.

    **IMPORTANT**: Call set_repository_config() first to specify repository type:
    - Public: Cyoda templates
    - Private: Your own repos

    Args:
        language: Programming language ('java' or 'python')
        branch_name: Branch name to create/checkout (pushed to remote if new)
        target_directory: Optional target directory (defaults to /tmp/cyoda_builds/<branch_name>)
        use_existing_branch: If True, checkout existing branch instead of creating new one
        tool_context: Execution context (auto-injected)

    Returns:
        Status message with repository path, or error if not configured
    """
    try:
        error_msg = await _validate_and_check_protected_branch(branch_name)
        if error_msg:
            return error_msg

        user_repo_url, installation_id, repo_type, config_error = (
            _get_repository_config_from_context(tool_context, language)
        )
        if config_error:
            return config_error

        repo_url, target_directory, repository_owner, repository_name, error_msg = (
            await _setup_repository_clone(
                language, user_repo_url, installation_id, repo_type,
                target_directory, branch_name
            )
        )
        if error_msg:
            return error_msg

        target_path = Path(target_directory)

        if target_path.exists() and (target_path / ".git").exists():
            return await _handle_already_cloned_repo(
                tool_context, target_directory, branch_name, language,
                repository_name, repository_owner, user_repo_url,
                installation_id, repo_type
            )

        error_msg = await _perform_clone_and_branch(
            repo_url, target_path, branch_name, use_existing_branch, user_repo_url
        )
        if error_msg:
            return error_msg

        conversation_id = tool_context.state.get("conversation_id") if tool_context else None
        return await _handle_push_and_finalize(
            target_path, branch_name, use_existing_branch, user_repo_url,
            installation_id, tool_context, conversation_id, language,
            repository_name, repository_owner, repo_type
        )

    except subprocess.TimeoutExpired:
        logger.error("Git operation timed out")
        return "ERROR: Git operation timed out"
    except Exception as e:
        logger.error(f"Failed to clone repository: {e}", exc_info=True)
        return f"ERROR: Failed to clone repository: {str(e)}"


__all__ = [
    # Public API
    "generate_branch_uuid",
    "check_existing_branch_configuration",
    "set_repository_config",
    "clone_repository",
    # Service dependencies (for test mocking)
    "get_entity_service",
    "_get_authenticated_repo_url_sync",
    # Re-exported for backward compatibility
    "BranchConfiguration",
    "_validate_tool_context",
    "_extract_config_from_tool_state",
    "_extract_config_from_conversation",
    "_detect_language",
    "_determine_repository_type",
    "_get_private_repo_config",
    "_get_public_repo_config",
    "_build_missing_context_error",
    "_build_no_config_error",
    "_build_invalid_repo_type_error",
    "_get_repository_config_from_context",
    "_handle_already_cloned_repo",
    "_handle_new_branch",
    "_handle_existing_branch",
    "_build_target_path",
    "_determine_repo_url",
    "_validate_and_check_protected_branch",
    "_extract_repo_name_and_owner",
    "_setup_repository_clone",
    "_handle_branch_setup",
    "_finalize_clone",
    "_format_clone_success_message",
    "_perform_clone_and_branch",
    "_handle_push_and_finalize",
]
