"""Conversation management functions for build context and task tracking."""

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.entity.conversation.version_1.conversation import Conversation
from .updates import _update_conversation_with_lock
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def _update_conversation_build_context(
    conversation_id: str, language: str, branch_name: str, repository_name: str, repository_owner: Optional[str] = None
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
        repository_owner: GitHub repository owner (if None, uses environment variable)
    """
    def update_fn(conversation: Conversation) -> None:
        # Update workflow_cache with build context AND repository info
        # NOTE: Repository fields (repositoryName, repositoryOwner, repositoryBranch)
        # are not in Cyoda schema, so we store them in workflowCache which IS persisted

        # Determine repository_owner: use parameter if provided, otherwise extract from URL if available,
        # otherwise fall back to environment variable
        owner = repository_owner
        if not owner and conversation.repository_url:
            try:
                from application.services.github.repository.url_parser import parse_repository_url
                url_info = parse_repository_url(conversation.repository_url)
                owner = url_info.owner
                logger.info(f"📦 Extracted repository_owner={owner} from repository_url={conversation.repository_url}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract owner from repository_url: {e}")
                owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")
        elif not owner:
            owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")

        conversation.workflow_cache["language"] = language
        conversation.workflow_cache["branch_name"] = branch_name
        conversation.workflow_cache["repository_name"] = repository_name
        conversation.workflow_cache["repository_owner"] = owner
        conversation.workflow_cache["repository_branch"] = branch_name

        logger.info(f"📋 Updated workflow_cache with language={language}, branch_name={branch_name}")
        logger.info(
            f"📦 Updated workflow_cache with repository info: "
            f"{owner}/{repository_name}@{branch_name}"
        )

        # Also update root-level fields (for Pydantic model compatibility, even though they won't persist in Cyoda)
        conversation.repository_name = repository_name
        conversation.repository_owner = owner
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
            total = len(conversation.background_task_ids)
            logger.info(f"📋 Added task {task_id} to background_task_ids. Total: {total}")
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


def _validate_tool_context(tool_context: Optional[ToolContext]) -> str:
    """Validate tool context and extract conversation ID.

    Args:
        tool_context: Execution context.

    Returns:
        Conversation ID

    Raises:
        ValueError: If context or conversation_id is invalid.
    """
    if not tool_context:
        raise ValueError("tool_context not available")

    conversation_id = tool_context.state.get("conversation_id")
    if not conversation_id:
        raise ValueError("conversation_id not found in context")

    return conversation_id


async def _get_conversation_entity(conversation_id: str) -> Optional[Conversation]:
    """Fetch conversation entity by ID.

    Args:
        conversation_id: Technical ID of the conversation.

    Returns:
        Conversation object or None if not found.
    """
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response:
            logger.error(f"Conversation {conversation_id} not found")
            return None

        conversation_data = response.data
        if isinstance(conversation_data, dict):
            return Conversation(**conversation_data)
        else:
            return conversation_data

    except Exception as e:
        logger.error(f"Failed to fetch conversation: {e}", exc_info=True)
        return None
