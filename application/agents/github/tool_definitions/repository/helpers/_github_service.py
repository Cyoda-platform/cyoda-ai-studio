"""Helper functions for GitHub service."""

from __future__ import annotations

import logging
import os

from google.adk.tools.tool_context import ToolContext

from application.entity.conversation import Conversation
from application.services.github.github_service import GitHubService
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def get_github_service_from_context(tool_context: ToolContext) -> GitHubService:
    """Get GitHubService instance from tool context.

    Uses installation_id from Conversation entity if available,
    otherwise falls back to environment variable.

    Args:
        tool_context: The ADK tool context

    Returns:
        GitHubService instance

    Raises:
        ValueError: If conversation_id not found or installation_id not available
    """
    conversation_id = tool_context.state.get("conversation_id")
    if not conversation_id:
        raise ValueError("conversation_id not found in tool context")

    # Get repository info from conversation
    entity_service = get_entity_service()
    conversation_response = await entity_service.get_by_id(
        entity_id=conversation_id,
        entity_class=Conversation.ENTITY_NAME,
        entity_version=str(Conversation.ENTITY_VERSION),
    )

    if not conversation_response:
        raise ValueError(f"Conversation {conversation_id} not found")

    # Handle conversation data (can be dict or object)
    conversation_data = conversation_response.data
    if isinstance(conversation_data, dict):
        # It's a dictionary - access directly
        installation_id_str = conversation_data.get("installation_id")
    else:
        # It's an object - use attribute access
        installation_id_str = getattr(conversation_data, "installation_id", None)

    # Fallback to environment variable if not in conversation
    if not installation_id_str:
        installation_id_str = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")
    if not installation_id_str:
        raise ValueError(
            "installation_id not found in Conversation entity or "
            "GITHUB_PUBLIC_REPO_INSTALLATION_ID environment variable"
        )

    installation_id = int(installation_id_str)
    logger.info(f"Using GitHub installation ID: {installation_id}")

    return GitHubService(installation_id=installation_id)
