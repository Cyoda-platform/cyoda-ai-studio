"""Helper functions for conversation and context operations."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def get_conversation_entity(
    tool_context: ToolContext,
    conversation_id: str,
) -> dict[str, Any] | None:
    """Retrieve conversation entity from the entity service.

    Args:
        tool_context: Tool context containing session state
        conversation_id: ID of the conversation to retrieve

    Returns:
        Conversation data dict or None if not found
    """
    try:
        from services.services import get_entity_service
        from application.entity.conversation.version_1.conversation import Conversation

        entity_service = get_entity_service()

        conversation_response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not conversation_response or not conversation_response.data:
            logger.warning(f"Could not retrieve conversation entity: {conversation_id}")
            return None

        # Convert to dict if needed
        conversation_data = (
            conversation_response.data
            if isinstance(conversation_response.data, dict)
            else conversation_response.data.model_dump(by_alias=False)
        )

        return conversation_data

    except Exception as e:
        logger.exception(f"Error retrieving conversation entity: {e}")
        return None


async def get_workflow_cache(
    tool_context: ToolContext,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Get workflow cache from conversation entity.

    Args:
        tool_context: Tool context containing session state
        conversation_id: Optional conversation ID (uses state if not provided)

    Returns:
        Workflow cache dictionary (empty dict if not found)
    """
    if not conversation_id:
        conversation_id = tool_context.state.get("conversation_id")

    if not conversation_id:
        logger.warning("No conversation_id provided or found in state")
        return {}

    conversation_data = await get_conversation_entity(tool_context, conversation_id)

    if not conversation_data:
        return {}

    workflow_cache = conversation_data.get("workflowCache", {})
    logger.info(f"Retrieved workflow_cache keys: {list(workflow_cache.keys())}")

    return workflow_cache
