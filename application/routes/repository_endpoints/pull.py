"""Pull repository endpoint."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from quart import request
from quart.typing import ResponseReturnValue

from application.routes.common.response import APIResponse
from application.routes.repository_endpoints.helpers import ensure_repository_cloned
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def _fetch_conversation(conversation_id: str) -> Tuple[Optional[Any], bool]:
    """Fetch conversation entity from entity service.

    Args:
        conversation_id: Technical ID of the conversation.

    Returns:
        Tuple of (conversation_data, success). Data is None if not found.
    """
    try:
        from application.entity.conversation.version_1.conversation import Conversation

        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response or not response.data:
            logger.error(f"Conversation {conversation_id} not found")
            return None, False

        return response.data, True

    except Exception as e:
        logger.error(f"Failed to fetch conversation: {e}", exc_info=True)
        return None, False


def _extract_repository_info(conversation_data: Any) -> Dict[str, Optional[str]]:
    """Extract repository information from conversation data.

    Handles both dict and object formats for backward compatibility.

    Args:
        conversation_data: Conversation data (dict or object).

    Returns:
        Dictionary with extracted repository info keys.
    """
    if isinstance(conversation_data, dict):
        return {
            "repository_path": (
                conversation_data.get("workflow_cache", {})
                .get("adk_session_state", {})
                .get("repository_path")
            ),
            "repository_branch": conversation_data.get("repository_branch"),
            "repository_url": conversation_data.get("repository_url"),
            "installation_id": conversation_data.get("installation_id"),
            "repository_name": conversation_data.get("repository_name"),
            "repository_owner": conversation_data.get("repository_owner"),
        }
    else:
        return {
            "repository_path": (
                getattr(conversation_data, "workflow_cache", {})
                .get("adk_session_state", {})
                .get("repository_path")
            ),
            "repository_branch": getattr(conversation_data, "repository_branch", None),
            "repository_url": getattr(conversation_data, "repository_url", None),
            "installation_id": getattr(conversation_data, "installation_id", None),
            "repository_name": getattr(conversation_data, "repository_name", None),
            "repository_owner": getattr(conversation_data, "repository_owner", None),
        }


def _verify_repository_exists(repository_path: Optional[str]) -> bool:
    """Verify repository exists and is a git repository.

    Args:
        repository_path: Path to repository.

    Returns:
        True if repository exists and is valid.
    """
    if not repository_path:
        return False

    repo_path_obj = Path(repository_path)
    return repo_path_obj.exists() and (repo_path_obj / ".git").exists()


class _SimpleToolContext:
    """Minimal tool context for calling GitHub tools.

    Provides state dictionary interface compatible with tool context.
    """

    def __init__(self, state: Dict[str, Any]):
        """Initialize with state dictionary.

        Args:
            state: State dictionary containing configuration.
        """
        self.state = state


def _format_pull_response(success: bool, message: str, branch: str) -> Dict[str, Any]:
    """Format pull repository response.

    Args:
        success: Whether pull operation succeeded.
        message: Result or error message.
        branch: Git branch name.

    Returns:
        Response dictionary.
    """
    return {"success": success, "message": message, "branch": branch}


async def handle_pull_repository() -> ResponseReturnValue:
    """Pull latest changes from remote repository.

    Request body:
        {
            "conversation_id": "uuid-of-conversation"
        }

    Returns:
        Success message with pulled changes summary.
    """
    try:
        # Extract and validate conversation ID
        data = await request.get_json()
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return APIResponse.error("conversation_id is required", 400)

        logger.info(f"Pulling repository changes for conversation: {conversation_id}")

        # Fetch conversation
        conversation_data, success = await _fetch_conversation(conversation_id)
        if not success:
            return APIResponse.error("Conversation not found", 404)

        # Extract repository information
        repo_info = _extract_repository_info(conversation_data)
        repository_path = repo_info["repository_path"]
        repository_branch = repo_info["repository_branch"]
        repository_url = repo_info["repository_url"]
        installation_id = repo_info["installation_id"]
        repository_name = repo_info["repository_name"]
        repository_owner = repo_info["repository_owner"]

        # Validate branch is configured
        if not repository_branch:
            return APIResponse.error("No branch configured for this conversation", 400)

        # Verify or clone repository
        if not _verify_repository_exists(repository_path):
            if not repository_url:
                return APIResponse.error(
                    "Repository not available and repository_url not configured. "
                    "Please ensure the conversation has repository_url configured.",
                    400,
                )

            logger.info(
                f"Repository not available at {repository_path}, attempting to clone from {repository_url}"
            )
            success, message, cloned_path = await ensure_repository_cloned(
                repository_url=repository_url,
                repository_branch=repository_branch,
                installation_id=installation_id,
                repository_name=repository_name,
                repository_owner=repository_owner,
                use_env_installation_id=True,
            )
            if not success:
                return APIResponse.error(f"Failed to clone repository: {message}", 400)

            repository_path = cloned_path
            logger.info(f"✅ Repository cloned successfully at {repository_path}")

        # Pull changes
        from application.agents.github.tools import pull_repository_changes

        tool_context = _SimpleToolContext(
            state={
                "conversation_id": conversation_id,
                "repository_path": repository_path,
            }
        )

        result = await pull_repository_changes(tool_context)

        if result.startswith("ERROR:"):
            return APIResponse.error(result, 500)

        # Format and return success response
        response = _format_pull_response(
            success=True, message=result, branch=repository_branch
        )
        return APIResponse.success(response)

    except Exception as e:
        logger.error(f"❌ Error pulling repository: {e}", exc_info=True)
        return APIResponse.error(
            "Failed to pull repository", 500, details={"message": str(e)}
        )
