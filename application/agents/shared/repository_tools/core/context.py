"""Context and entity update functions for repository management."""

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.entity.conversation.version_1.conversation import Conversation
from services.services import get_entity_service

logger = logging.getLogger(__name__)


def _store_in_tool_context(
    tool_context: ToolContext,
    repository_path: str,
    branch_name: str,
    language: str,
    repository_name: str,
    repository_owner: str,
    user_repo_url: Optional[str],
    installation_id: Optional[str],
    repo_type: Optional[str],
) -> None:
    """Store repository information in tool context.

    Args:
        tool_context: Tool context to update
        repository_path: Path to cloned repository
        branch_name: Branch name
        language: Programming language
        repository_name: Repository name
        repository_owner: Repository owner
        user_repo_url: User's repository URL
        installation_id: GitHub installation ID
        repo_type: Repository type (public/private)
    """
    tool_context.state["repository_path"] = repository_path
    tool_context.state["branch_name"] = branch_name
    tool_context.state["language"] = language
    tool_context.state["repository_name"] = repository_name
    tool_context.state["repository_owner"] = repository_owner
    tool_context.state["repository_url"] = user_repo_url
    tool_context.state["installation_id"] = installation_id
    if repo_type and "repository_type" not in tool_context.state:
        tool_context.state["repository_type"] = repo_type


async def _update_conversation_entity(
    conversation_id: str,
    repository_name: str,
    repository_owner: str,
    branch_name: str,
    user_repo_url: Optional[str],
    installation_id: Optional[str],
) -> None:
    """Update Conversation entity with repository information.

    Args:
        conversation_id: Conversation ID
        repository_name: Repository name
        repository_owner: Repository owner
        branch_name: Branch name
        user_repo_url: User's repository URL
        installation_id: GitHub installation ID
    """
    try:
        logger.info(
            f"🔄 Updating Conversation entity {conversation_id} with: "
            f"repo={repository_name}, branch={branch_name}, owner={repository_owner}"
        )

        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response or not response.data:
            logger.error(
                f"❌ Cannot update Conversation entity: conversation {conversation_id} not found or has no data"
            )
            return

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

        logger.info(
            f"📝 Persisting Conversation entity update: "
            f"repo={conversation.repository_name}, "
            f"branch={conversation.repository_branch}, "
            f"owner={conversation.repository_owner}"
        )

        # Persist updated conversation
        entity_dict = conversation.model_dump(by_alias=False)
        await entity_service.update(
            entity_id=conversation_id,
            entity=entity_dict,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )
        logger.info(
            f"✅ Successfully updated Conversation entity with repository_branch={branch_name}"
        )
    except Exception as e:
        logger.error(
            f"❌ Failed to update Conversation entity {conversation_id}: {e}",
            exc_info=True,
        )


async def _update_conversation_build_context_wrapper(
    conversation_id: str,
    language: str,
    branch_name: str,
    repository_name: str,
    repository_owner: Optional[str] = None,
) -> None:
    """Update conversation build context for setup agent.

    Args:
        conversation_id: Conversation ID
        language: Programming language
        branch_name: Branch name
        repository_name: Repository name
        repository_owner: Repository owner (optional)
    """
    try:
        from application.agents.shared.repository_tools.conversation import (
            _update_conversation_build_context,
        )

        await _update_conversation_build_context(
            conversation_id=conversation_id,
            language=language,
            branch_name=branch_name,
            repository_name=repository_name,
            repository_owner=repository_owner,
        )
        logger.info(f"✅ Updated conversation workflow_cache with build context")
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to update conversation build context: {e}", exc_info=True
        )
