"""Conversation management helpers for environment agent tools.

This module handles conversation state updates to separate
persistence concerns from tool logic.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def _fetch_conversation_entity(
    conversation_id: str,
) -> Optional[any]:
    """Fetch conversation entity by ID.

    Args:
        conversation_id: Conversation ID

    Returns:
        Conversation response or None
    """
    from application.entity.conversation.version_1.conversation import Conversation
    from services.services import get_entity_service

    entity_service = get_entity_service()
    response = await entity_service.get_by_id(
        entity_id=conversation_id,
        entity_class=Conversation.ENTITY_NAME,
        entity_version=str(Conversation.ENTITY_VERSION),
    )

    if not response or not response.data:
        logger.warning(f"Conversation {conversation_id} not found")
        return None

    return response


def _parse_conversation_data(response: any) -> dict:
    """Parse conversation response data into dictionary.

    Args:
        response: Entity service response

    Returns:
        Conversation data as dictionary
    """
    conversation_data = (
        response.data
        if isinstance(response.data, dict)
        else response.data.model_dump(by_alias=False)
    )
    return conversation_data


def _update_workflow_cache(conversation: any, build_id: str, namespace: str) -> None:
    """Update conversation workflow_cache with deployment info.

    Args:
        conversation: Conversation object
        build_id: Build ID
        namespace: Deployment namespace
    """
    conversation.workflow_cache["build_id"] = build_id
    conversation.workflow_cache["namespace"] = namespace
    logger.info(f"Updated workflow_cache: build_id={build_id}, namespace={namespace}")


async def _persist_conversation(conversation_id: str, conversation: any) -> None:
    """Persist conversation changes to database.

    Args:
        conversation_id: Conversation ID
        conversation: Conversation object
    """
    from application.entity.conversation.version_1.conversation import Conversation
    from services.services import get_entity_service

    entity_service = get_entity_service()
    entity_dict = conversation.model_dump(by_alias=False)

    await entity_service.update(
        entity_id=conversation_id,
        entity=entity_dict,
        entity_class=Conversation.ENTITY_NAME,
        entity_version=str(Conversation.ENTITY_VERSION),
    )


async def update_conversation_workflow_cache(
    conversation_id: str,
    build_id: str,
    namespace: str,
) -> bool:
    """Update conversation workflow_cache with deployment information.

    Args:
        conversation_id: Conversation ID
        build_id: Build ID
        namespace: Deployment namespace

    Returns:
        True if update successful, False otherwise
    """
    try:
        from application.entity.conversation.version_1.conversation import Conversation

        # Fetch conversation entity
        response = await _fetch_conversation_entity(conversation_id)
        if not response:
            return False

        # Parse conversation data
        conversation_data = _parse_conversation_data(response)
        conversation = Conversation(**conversation_data)

        # Update workflow cache
        _update_workflow_cache(conversation, build_id, namespace)

        # Persist changes
        await _persist_conversation(conversation_id, conversation)

        logger.info(
            f"Successfully updated conversation {conversation_id} workflow_cache"
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to update conversation workflow_cache: {e}")
        # Non-critical - don't fail deployment
        return False
