"""Conversation persistence operations for OpenAI Assistant."""

import asyncio
import logging
from typing import Any

from common.service.service import EntityServiceError

logger = logging.getLogger(__name__)


async def persist_conversation(
    entity_service: Any,
    conversation_id: str,
    conversation_history: list[dict[str, str]],
    user_id: str,
) -> None:
    """Persist conversation to Cyoda.

    Args:
        entity_service: Cyoda entity service for persistence
        conversation_id: Cyoda Conversation technical ID
        conversation_history: Updated conversation history
        user_id: User ID
    """
    try:
        logger.debug(f"Persisting conversation {conversation_id}")

        # Get the conversation entity
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class="Conversation",
            entity_version="1",
        )

        if not response:
            logger.warning(f"Conversation {conversation_id} not found")
            return

        # Update workflow_cache with conversation history
        # response.data is already a dict, not a Pydantic model
        conversation_data = (
            response.data
            if isinstance(response.data, dict)
            else response.data.model_dump()
        )
        conversation_data["workflow_cache"] = {
            "conversation_history": conversation_history,
            "last_updated": asyncio.get_event_loop().time(),
        }

        # Save updated conversation
        await entity_service.update(
            entity_id=conversation_id,
            entity=conversation_data,
            entity_class="Conversation",
            entity_version="1",
        )

        logger.debug(f"Conversation {conversation_id} persisted successfully")

    except EntityServiceError as e:
        logger.error(f"Error persisting conversation: {e}")
        # Don't raise - persistence failure shouldn't break the conversation
    except Exception as e:
        logger.exception(f"Unexpected error persisting conversation: {e}")


def build_prompt(
    user_message: str,
    conversation_history: list[dict[str, str]],
) -> str:
    """Build a full prompt from conversation history and current message.

    Args:
        user_message: Current user message
        conversation_history: Previous conversation messages

    Returns:
        Formatted prompt string
    """
    if not conversation_history:
        return user_message

    # Format conversation history
    history_lines = []
    for msg in conversation_history:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        history_lines.append(f"{role}: {content}")

    # Add current message
    history_lines.append(f"User: {user_message}")

    return "\n".join(history_lines)
