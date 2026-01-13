"""Repository configuration and validation functions."""

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from application.agents.shared.repository_tools.constants import (
    GITHUB_PUBLIC_REPO_INSTALLATION_ID,
    JAVA_PUBLIC_REPO_URL,
    PYTHON_PUBLIC_REPO_URL,
)
from application.entity.conversation.version_1.conversation import Conversation
from services.services import get_entity_service

logger = logging.getLogger(__name__)

# Configuration constants
PYTHON_REPO_NAME = "mcp-cyoda-quart-app"
JAVA_REPO_NAME = "java-client-template"


class BranchConfiguration(BaseModel):
    """Structured branch configuration from conversation."""

    configured: bool
    language: Optional[str] = None
    repository_type: Optional[str] = None
    repository_name: Optional[str] = None
    repository_owner: Optional[str] = None
    repository_branch: Optional[str] = None
    repository_url: Optional[str] = None
    installation_id: Optional[str] = None
    repository_path: Optional[str] = None
    ready_to_build: bool = False
    error: Optional[str] = None
    message: Optional[str] = None


def _validate_tool_context(
    tool_context: Optional[ToolContext],
) -> tuple[bool, Optional[str], Optional[str]]:
    """Validate tool context and extract conversation ID.

    Args:
        tool_context: Execution context

    Returns:
        Tuple of (is_valid, error_message, conversation_id)
    """
    if not tool_context:
        return False, "Tool context not available", None

    conversation_id = tool_context.state.get("conversation_id")
    if not conversation_id:
        return False, "No conversation_id found in context", None

    return True, None, conversation_id


def _extract_config_from_tool_state(tool_context: ToolContext) -> dict:
    """Extract repository configuration from tool context state.

    Args:
        tool_context: Execution context

    Returns:
        Dictionary with repository configuration fields
    """
    return {
        "repository_name": tool_context.state.get("repository_name"),
        "repository_owner": tool_context.state.get("repository_owner"),
        "repository_branch": tool_context.state.get("branch_name"),
        "repository_url": tool_context.state.get("repository_url"),
        "installation_id": tool_context.state.get("installation_id"),
        "repository_path": tool_context.state.get("repository_path"),
    }


async def _extract_config_from_conversation(
    conversation_id: str, existing_config: dict
) -> tuple[bool, Optional[str], dict]:
    """Extract repository configuration from conversation entity.

    Args:
        conversation_id: Conversation ID
        existing_config: Already extracted configuration to merge with

    Returns:
        Tuple of (success, error_message, merged_config)
    """
    try:
        entity_service = get_entity_service()
        conversation_response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not conversation_response:
            logger.warning(f"❌ Conversation {conversation_id} not found in database")
            return False, f"Conversation {conversation_id} not found", existing_config

        # Handle conversation data (can be dict or object)
        conversation_data = conversation_response.data
        merged_config = existing_config.copy()

        if isinstance(conversation_data, dict):
            merged_config["repository_name"] = merged_config[
                "repository_name"
            ] or conversation_data.get("repository_name")
            merged_config["repository_owner"] = merged_config[
                "repository_owner"
            ] or conversation_data.get("repository_owner")
            merged_config["repository_branch"] = merged_config[
                "repository_branch"
            ] or conversation_data.get("repository_branch")
            merged_config["repository_url"] = merged_config[
                "repository_url"
            ] or conversation_data.get("repository_url")
            merged_config["installation_id"] = merged_config[
                "installation_id"
            ] or conversation_data.get("installation_id")

            logger.info(
                f"📦 Extracted from Conversation entity (dict): "
                f"repo={conversation_data.get('repository_name')}, "
                f"branch={conversation_data.get('repository_branch')}, "
                f"owner={conversation_data.get('repository_owner')}"
            )
        else:
            merged_config["repository_name"] = merged_config[
                "repository_name"
            ] or getattr(conversation_data, "repository_name", None)
            merged_config["repository_owner"] = merged_config[
                "repository_owner"
            ] or getattr(conversation_data, "repository_owner", None)
            merged_config["repository_branch"] = merged_config[
                "repository_branch"
            ] or getattr(conversation_data, "repository_branch", None)
            merged_config["repository_url"] = merged_config[
                "repository_url"
            ] or getattr(conversation_data, "repository_url", None)
            merged_config["installation_id"] = merged_config[
                "installation_id"
            ] or getattr(conversation_data, "installation_id", None)

            logger.info(
                f"📦 Extracted from Conversation entity (object): "
                f"repo={getattr(conversation_data, 'repository_name', None)}, "
                f"branch={getattr(conversation_data, 'repository_branch', None)}, "
                f"owner={getattr(conversation_data, 'repository_owner', None)}"
            )

        return True, None, merged_config

    except Exception as e:
        logger.error(
            f"Error extracting configuration from conversation: {e}", exc_info=True
        )
        return False, str(e), existing_config


def _detect_language(repository_name: str) -> Optional[str]:
    """Detect programming language from repository name.

    Args:
        repository_name: Name of the repository

    Returns:
        Language ('python', 'java') or None if not detected
    """
    if repository_name == PYTHON_REPO_NAME:
        return "python"
    elif repository_name == JAVA_REPO_NAME:
        return "java"
    elif "python" in repository_name.lower():
        return "python"
    elif "java" in repository_name.lower():
        return "java"

    return None


def _determine_repository_type(
    repository_url: Optional[str], installation_id: Optional[str]
) -> str:
    """Determine repository type based on configuration.

    Args:
        repository_url: Repository URL
        installation_id: Installation ID

    Returns:
        Repository type ('private' or 'public')
    """
    return "private" if repository_url and installation_id else "public"


def _get_private_repo_config(
    tool_context: ToolContext,
) -> tuple[Optional[str], Optional[str]]:
    """Get private repository configuration from context.

    Args:
        tool_context: Tool context

    Returns:
        Tuple of (repo_url, installation_id)
    """
    user_repo_url = tool_context.state.get("user_repository_url")
    installation_id = tool_context.state.get("installation_id")
    logger.info(
        f"📦 Private repo mode: {user_repo_url}, installation_id={installation_id}"
    )
    return user_repo_url, installation_id


def _build_missing_context_error() -> str:
    """Build error message for missing tool context."""
    return (
        "❌ Repository configuration required before cloning.\n\n"
        "Tool context is not available. Please ensure you're using this tool within a proper "
        "conversation context and have configured your repository settings using `set_repository_config()`."
    )


def _build_no_config_error() -> str:
    """Build error message for missing repository configuration."""
    return (
        "❌ Repository configuration required before cloning.\n\n"
        "Please specify your repository type first:\n\n"
        "**For Public Repositories (Cyoda templates):**\n"
        "Use: `set_repository_config(repository_type='public')`\n"
        "This will use Cyoda's public templates and push to the public repository.\n\n"
        "**For Private Repositories:**\n"
        "Use: `set_repository_config(repository_type='private', "
        "installation_id='YOUR_ID', repository_url='YOUR_REPO_URL')`\n"
        "This requires your GitHub App to be installed on your private repository.\n\n"
        "💡 **Need help?** The repository type determines where your code will be stored and pushed."
    )


def _build_invalid_repo_type_error(repo_type: str) -> str:
    """Build error message for invalid repository type.

    Args:
        repo_type: Invalid repository type value

    Returns:
        Error message string
    """
    return f"Invalid repository_type '{repo_type}'. Must be 'public' or 'private'."


def _get_public_repo_config(
    language: str,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Get public repository configuration based on language.

    Args:
        language: Programming language

    Returns:
        Tuple of (repo_url, installation_id, error_msg)
    """
    if language.lower() == "python":
        repo_url = PYTHON_PUBLIC_REPO_URL
    elif language.lower() == "java":
        repo_url = JAVA_PUBLIC_REPO_URL
    else:
        return None, None, f"Unsupported language '{language}'"

    installation_id = GITHUB_PUBLIC_REPO_INSTALLATION_ID
    logger.info(f"📦 Public repo mode: {repo_url}, installation_id={installation_id}")
    return repo_url, installation_id, None


def _get_repository_config_from_context(
    tool_context: Optional[ToolContext], language: str
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Extract repository configuration from tool context.

    Args:
        tool_context: Tool context (may be None)
        language: Programming language

    Returns:
        Tuple of (repo_url, installation_id, repo_type, error_message)
        If error_message is not None, an error occurred
    """
    if not tool_context:
        error_msg = _build_missing_context_error()
        return None, None, None, f"ERROR: {error_msg}"

    repo_type = tool_context.state.get("repository_type")

    if repo_type == "private":
        user_repo_url, installation_id = _get_private_repo_config(tool_context)
        return user_repo_url, installation_id, repo_type, None

    elif repo_type == "public":
        repo_url, installation_id, error = _get_public_repo_config(language)
        if error:
            return None, None, None, f"ERROR: {error}"
        return repo_url, installation_id, repo_type, None

    elif repo_type is None:
        error_msg = _build_no_config_error()
        return None, None, None, f"ERROR: {error_msg}"

    else:
        error_msg = _build_invalid_repo_type_error(repo_type)
        return None, None, None, f"ERROR: {error_msg}"
