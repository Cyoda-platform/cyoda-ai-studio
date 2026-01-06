"""Debug history persistence operations."""

import logging
from typing import Any, Dict, List, Optional

from .content_builders import (
    build_debug_history_content,
    build_edge_message_meta,
    build_response_debug_history,
    build_response_edge_message,
)
from .message_operations import save_to_repository

logger = logging.getLogger(__name__)

# Response persistence constants
RESPONSE_LOG_SUCCESS = "✅ Saved response with debug history as edge message {edge_message_id}"
RESPONSE_LOG_FAILURE = "Failed to save response with debug history"
RESPONSE_LOG_ERROR = "❌ Error saving response with debug history: {error}"


async def save_streaming_debug_history(
    repository: Any,
    conversation_id: str,
    user_id: str,
    streaming_events: List[Dict[str, Any]],
    response_summary: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Save streaming debug history as an edge message.

    Args:
        repository: Repository instance
        conversation_id: The conversation ID
        user_id: The user ID
        streaming_events: List of streaming events from the stream
        response_summary: Optional summary of the response

    Returns:
        Edge message ID if successful, None otherwise
    """
    try:
        # Build debug history content
        debug_history = build_debug_history_content(
            conversation_id, user_id, streaming_events, response_summary
        )

        # Build metadata (reuse existing helper)
        meta = build_edge_message_meta()

        # Save to repository
        edge_message_id = await save_to_repository(repository, meta, debug_history)

        if edge_message_id:
            logger.info(
                f"✅ Saved streaming debug history as edge message {edge_message_id} "
                f"({len(streaming_events)} events)"
            )
            return edge_message_id
        else:
            logger.error("❌ Failed to save streaming debug history as edge message")
            return None

    except Exception as e:
        logger.exception(f"Error saving streaming debug history: {e}")
        return None


async def save_response_with_history(
    repository: Any,
    conversation_id: str,
    user_id: str,
    response_content: str,
    streaming_events: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Save response with streaming debug history in a single edge message.

    Args:
        repository: Repository instance
        conversation_id: The conversation ID
        user_id: The user ID
        response_content: The AI response content
        streaming_events: List of streaming events
        metadata: Optional metadata (hooks, etc.)

    Returns:
        Edge message ID if successful, None otherwise

    Example:
        >>> edge_id = await save_response_with_history(
        ...     repo,
        ...     conversation_id="conv-123",
        ...     user_id="user-456",
        ...     response_content="This is a response",
        ...     streaming_events=[{"type": "chunk", "data": "This"}],
        ...     metadata={"hooks": []}
        ... )
    """
    try:
        # Step 1: Build debug history from streaming events
        debug_history = build_response_debug_history(streaming_events)

        # Step 2: Build edge message content
        edge_message = build_response_edge_message(
            conversation_id, user_id, response_content, metadata, debug_history
        )

        # Step 3: Build entity metadata
        meta = build_edge_message_meta()

        # Step 4: Save to repository
        edge_message_id = await save_to_repository(repository, meta, edge_message.model_dump())

        # Step 5: Log result and return
        if edge_message_id:
            logger.info(RESPONSE_LOG_SUCCESS.format(edge_message_id=edge_message_id))
            return edge_message_id

        logger.error(RESPONSE_LOG_FAILURE)
        return None

    except Exception as e:
        logger.error(RESPONSE_LOG_ERROR.format(error=e))
        return None
