"""Conversation update and persistence functions."""

import asyncio
import logging
from typing import Callable, Optional

from application.agents.shared.repository_tools.constants import (
    INITIAL_RETRY_DELAY_SECONDS,
    MAX_LOCK_RETRIES,
)
from application.entity.conversation.version_1.conversation import Conversation
from services.services import get_entity_service

from .locking import (
    _acquire_lock,
    _calculate_next_retry_delay,
    _fetch_conversation,
    _release_lock,
)

logger = logging.getLogger(__name__)


async def _persist_and_verify_update(
    conversation_id: str,
    entity_dict: dict,
    description: str,
) -> bool:
    """Persist conversation update and verify persistence.

    Args:
        conversation_id: Technical ID of the conversation.
        entity_dict: Conversation entity as dictionary.
        description: Description for logging.

    Returns:
        True if update persisted successfully.
    """
    try:
        logger.info(f"🔍 [{description}] Sending update request with locked=False...")
        logger.info(f"🔍 [{description}] Entity dict keys: {list(entity_dict.keys())}")

        entity_service = get_entity_service()
        update_response = await entity_service.update(
            entity_id=conversation_id,
            entity=entity_dict,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        logger.info(f"✅ [{description}] Update response: {update_response}")

        # Verify persistence by fetching immediately after
        logger.info(f"🔍 [{description}] Verifying update by fetching entity...")
        verify_response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if verify_response and verify_response.data:
            verify_data = (
                verify_response.data
                if isinstance(verify_response.data, dict)
                else verify_response.data.model_dump(by_alias=False)
            )
            logger.info(
                f"✅ [{description}] VERIFICATION - repositoryName={verify_data.get('repositoryName')}, "
                f"repositoryOwner={verify_data.get('repositoryOwner')}, "
                f"repositoryBranch={verify_data.get('repositoryBranch')}, locked={verify_data.get('locked')}"
            )

            # Check if fields were actually persisted
            if entity_dict.get("repositoryName") and not verify_data.get(
                "repositoryName"
            ):
                logger.error(
                    f"❌ [{description}] VERIFICATION FAILED: repositoryName was not persisted! "
                    f"Sent: {entity_dict.get('repositoryName')}, Got: {verify_data.get('repositoryName')}"
                )
            if entity_dict.get("repositoryOwner") and not verify_data.get(
                "repositoryOwner"
            ):
                logger.error(
                    f"❌ [{description}] VERIFICATION FAILED: repositoryOwner was not persisted! "
                    f"Sent: {entity_dict.get('repositoryOwner')}, Got: {verify_data.get('repositoryOwner')}"
                )
            if entity_dict.get("repositoryBranch") and not verify_data.get(
                "repositoryBranch"
            ):
                logger.error(
                    f"❌ [{description}] VERIFICATION FAILED: repositoryBranch was not persisted! "
                    f"Sent: {entity_dict.get('repositoryBranch')}, Got: {verify_data.get('repositoryBranch')}"
                )
            return True
        else:
            logger.warning(
                f"⚠️ [{description}] Could not verify update - entity not found"
            )
            return True  # Update succeeded even if verification failed

    except Exception as e:
        logger.error(f"❌ [{description}] Failed to persist update: {e}", exc_info=True)
        return False


async def _update_conversation_with_lock(
    conversation_id: str, update_fn: Callable, description: str = "update"
) -> bool:
    """Update conversation entity with pessimistic locking.

    Implements centralized locking mechanism to prevent race conditions when
    multiple agents/processes update the same conversation simultaneously.

    Args:
        conversation_id: Technical ID of the conversation.
        update_fn: Function that takes Conversation object and modifies it in-place.
        description: Description of the update for logging.

    Returns:
        True if update succeeded, False otherwise.
    """
    max_retries = MAX_LOCK_RETRIES
    retry_delay = INITIAL_RETRY_DELAY_SECONDS

    for attempt in range(max_retries):
        try:
            logger.info(
                f"🔒 [{description}] Attempting to acquire lock (attempt {attempt + 1}/{max_retries}): "
                f"conversation_id={conversation_id}"
            )

            # Fetch fresh conversation data before attempting lock
            conversation, success = await _fetch_conversation(conversation_id)
            if not success:
                return False

            # Log state before changes
            logger.info(
                f"📊 [{description}] BEFORE update - repositoryName={conversation.repository_name}, "
                f"repositoryOwner={conversation.repository_owner}, "
                f"repositoryBranch={conversation.repository_branch}, locked={conversation.locked}"
            )

            # Check if already locked by another process
            if conversation.locked:
                logger.warning(
                    f"🔒 [{description}] Conversation is locked, waiting {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay = _calculate_next_retry_delay(retry_delay)
                continue

            # Try to acquire lock
            lock_acquired = await _acquire_lock(conversation_id)
            if not lock_acquired:
                await asyncio.sleep(retry_delay)
                retry_delay = _calculate_next_retry_delay(retry_delay)
                continue

            # Lock acquired - fetch fresh data and apply update
            success = await _apply_update_and_persist(
                conversation_id, update_fn, description
            )

            if success:
                logger.info(
                    f"✅ [{description}] Successfully updated conversation {conversation_id}"
                )
                return True

            # Update failed - release lock and retry
            await _release_lock(conversation_id, description)
            await asyncio.sleep(retry_delay)
            retry_delay = _calculate_next_retry_delay(retry_delay)

        except Exception as e:
            logger.error(
                f"❌ [{description}] Unexpected error in lock acquisition: {e}",
                exc_info=True,
            )
            await asyncio.sleep(retry_delay)
            retry_delay = _calculate_next_retry_delay(retry_delay)

    logger.error(
        f"❌ [{description}] Failed to update conversation after {max_retries} attempts"
    )
    return False


async def _apply_update_and_persist(
    conversation_id: str,
    update_fn: Callable,
    description: str,
) -> bool:
    """Apply update function and persist changes with verification.

    Args:
        conversation_id: Technical ID of the conversation.
        update_fn: Function to apply to conversation.
        description: Description for logging.

    Returns:
        True if update persisted successfully.
    """
    try:
        # Fetch fresh data after acquiring lock
        logger.info(
            f"📥 [{description}] Fetching fresh conversation data after lock acquisition..."
        )
        conversation, success = await _fetch_conversation(conversation_id)
        if not success:
            return False

        # Apply the update function
        update_fn(conversation)

        # Release lock before persisting
        conversation.locked = False
        entity_dict = conversation.model_dump(by_alias=False)

        logger.info(
            f"🔍 [{description}] Sending - repositoryName={entity_dict.get('repositoryName')}, "
            f"repositoryOwner={entity_dict.get('repositoryOwner')}, "
            f"repositoryBranch={entity_dict.get('repositoryBranch')}"
        )

        # Persist and verify update
        return await _persist_and_verify_update(
            conversation_id, entity_dict, description
        )

    except Exception as e:
        logger.error(f"❌ [{description}] Failed to apply update: {e}", exc_info=True)
        return False
