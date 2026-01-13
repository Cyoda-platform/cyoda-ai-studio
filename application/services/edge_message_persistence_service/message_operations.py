"""Message persistence operations."""

import logging
from typing import Any, Dict, List, Optional

from .content_builders import (
    build_edge_message_content,
    build_edge_message_meta,
)

logger = logging.getLogger(__name__)


async def save_to_repository(
    repository: Any,
    meta: Dict[str, Any],
    content: Dict[str, Any],
) -> Optional[str]:
    """Save edge message to repository.

    Args:
        repository: Repository instance
        meta: Entity metadata
        content: Edge message content

    Returns:
        Edge message ID or None
    """
    return await repository.save(meta=meta, entity=content)


async def save_message_as_edge_message(
    repository: Any,
    message_type: str,
    message_content: str,
    conversation_id: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    file_blob_ids: Optional[List[str]] = None,
) -> Optional[str]:
    """Save a message as an edge message.

    Args:
        repository: Repository instance
        message_type: Type of message ('user', 'ai', 'error', etc.)
        message_content: The message content
        conversation_id: The conversation ID
        user_id: The user ID
        metadata: Optional metadata (hooks, etc.)
        file_blob_ids: Optional file attachments

    Returns:
        Edge message ID if successful, None otherwise
    """
    try:
        # Build edge message content
        edge_message_content = build_edge_message_content(
            message_type,
            message_content,
            conversation_id,
            user_id,
            metadata,
            file_blob_ids,
        )

        # Build metadata
        meta = build_edge_message_meta()

        # Save to repository
        edge_message_id = await save_to_repository(
            repository, meta, edge_message_content
        )

        if edge_message_id:
            logger.info(
                f"✅ Saved {message_type} message as edge message {edge_message_id}"
            )
            return edge_message_id
        else:
            logger.error(f"❌ Failed to save {message_type} message as edge message")
            return None

    except Exception as e:
        logger.exception(f"Error saving message as edge message: {e}")
        return None
