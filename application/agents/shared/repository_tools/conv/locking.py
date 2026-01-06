"""Conversation locking functions for pessimistic concurrency control."""

import asyncio
import logging
from typing import Optional

from application.agents.shared.repository_tools.constants import (
    INITIAL_RETRY_DELAY_SECONDS,
    MAX_LOCK_RETRIES,
    MAX_RETRY_DELAY_SECONDS,
)
from application.entity.conversation.version_1.conversation import Conversation
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def _fetch_conversation(conversation_id: str) -> tuple[Optional[Conversation], bool]:
    """Fetch a conversation entity by ID.

    Args:
        conversation_id: Technical ID of the conversation.

    Returns:
        Tuple of (conversation, success). Conversation is None if not found.
    """
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response or not response.data:
            logger.warning(f"⚠️ Conversation {conversation_id} not found")
            return None, False

        if isinstance(response.data, dict):
            conversation_data = response.data
        else:
            conversation_data = response.data.model_dump(by_alias=False)
        conversation = Conversation(**conversation_data)
        return conversation, True

    except Exception as e:
        logger.error(f"❌ Failed to fetch conversation: {e}", exc_info=True)
        return None, False


async def _acquire_lock(conversation_id: str) -> bool:
    """Acquire lock on conversation entity.

    Args:
        conversation_id: Technical ID of the conversation.

    Returns:
        True if lock acquired successfully.
    """
    try:
        conversation, success = await _fetch_conversation(conversation_id)
        if not success or conversation is None:
            return False

        logger.info(f"🔒 Sending lock acquisition request for conversation {conversation_id}...")
        conversation.locked = True
        entity_dict = conversation.model_dump(by_alias=False)

        entity_service = get_entity_service()
        await entity_service.update(
            entity_id=conversation_id,
            entity=entity_dict,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        logger.info(f"🔒 Lock acquired for conversation {conversation_id}")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Failed to acquire lock (version conflict): {e}")
        return False


async def _release_lock(conversation_id: str, description: str) -> bool:
    """Release lock on conversation entity.

    Args:
        conversation_id: Technical ID of the conversation.
        description: Description for logging.

    Returns:
        True if lock released successfully.
    """
    try:
        logger.info(f"🔓 [{description}] Attempting to release lock...")
        conversation, success = await _fetch_conversation(conversation_id)
        if not success or conversation is None:
            logger.warning(f"⚠️ Could not fetch conversation for lock release")
            return False

        conversation.locked = False
        entity_dict = conversation.model_dump(by_alias=False)

        entity_service = get_entity_service()
        await entity_service.update(
            entity_id=conversation_id,
            entity=entity_dict,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        logger.info(f"🔓 [{description}] Released lock")
        return True

    except Exception as e:
        logger.error(f"❌ [{description}] Failed to release lock: {e}", exc_info=True)
        return False


def _calculate_next_retry_delay(current_delay: float) -> float:
    """Calculate next retry delay with exponential backoff.

    Args:
        current_delay: Current delay in seconds.

    Returns:
        Next delay in seconds, capped at MAX_RETRY_DELAY_SECONDS.
    """
    return min(current_delay * 1.5, MAX_RETRY_DELAY_SECONDS)
