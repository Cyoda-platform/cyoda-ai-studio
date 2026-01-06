"""Edge Message Persistence Service - Re-exports for backward compatibility."""

from .content_builders import (
    DebugHistoryData,
    ResponseEdgeMessageContent,
    MESSAGE_EDGE_TYPE,
    DEFAULT_FILE_BLOB_IDS,
    RESPONSE_MESSAGE_TYPE,
    DEBUG_HISTORY_TYPE,
    build_edge_message_content,
    build_edge_message_meta,
    build_debug_history_content,
    build_response_debug_history,
    build_response_edge_message,
)
from .message_operations import (
    save_to_repository,
    save_message_as_edge_message,
)
from .debug_history import (
    save_streaming_debug_history,
    save_response_with_history,
    RESPONSE_LOG_SUCCESS,
    RESPONSE_LOG_FAILURE,
    RESPONSE_LOG_ERROR,
)


class EdgeMessagePersistenceService:
    """Service for persisting messages as edge messages."""

    def __init__(self, repository):
        """Initialize the persistence service.

        Args:
            repository: The Cyoda repository for saving edge messages
        """
        self.repository = repository

    def _build_edge_message_content(
        self,
        message_type: str,
        message_content: str,
        conversation_id: str,
        user_id: str,
        metadata,
        file_blob_ids,
    ):
        """Build edge message content dictionary."""
        return build_edge_message_content(
            message_type,
            message_content,
            conversation_id,
            user_id,
            metadata,
            file_blob_ids,
        )

    def _build_edge_message_meta(self):
        """Build edge message metadata for Cyoda entity."""
        return build_edge_message_meta()

    async def _save_to_repository(self, meta, content):
        """Save edge message to repository."""
        return await save_to_repository(self.repository, meta, content)

    async def save_message_as_edge_message(
        self,
        message_type: str,
        message_content: str,
        conversation_id: str,
        user_id: str,
        metadata=None,
        file_blob_ids=None,
    ):
        """Save a message as an edge message."""
        return await save_message_as_edge_message(
            self.repository,
            message_type,
            message_content,
            conversation_id,
            user_id,
            metadata,
            file_blob_ids,
        )

    def _build_debug_history_content(
        self, conversation_id, user_id, streaming_events, response_summary
    ):
        """Build debug history content dictionary."""
        return build_debug_history_content(
            conversation_id, user_id, streaming_events, response_summary
        )

    async def save_streaming_debug_history(
        self, conversation_id, user_id, streaming_events, response_summary=None
    ):
        """Save streaming debug history as an edge message."""
        return await save_streaming_debug_history(
            self.repository,
            conversation_id,
            user_id,
            streaming_events,
            response_summary,
        )

    def _build_response_debug_history(self, streaming_events):
        """Build debug history data structure for response."""
        return build_response_debug_history(streaming_events)

    def _build_response_edge_message(
        self, conversation_id, user_id, response_content, metadata, debug_history
    ):
        """Build edge message content for response with history."""
        return build_response_edge_message(
            conversation_id, user_id, response_content, metadata, debug_history
        )

    async def save_response_with_history(
        self,
        conversation_id,
        user_id,
        response_content,
        streaming_events,
        metadata=None,
    ):
        """Save response with streaming debug history in a single edge message."""
        return await save_response_with_history(
            self.repository,
            conversation_id,
            user_id,
            response_content,
            streaming_events,
            metadata,
        )


__all__ = [
    "EdgeMessagePersistenceService",
    "DebugHistoryData",
    "ResponseEdgeMessageContent",
    "MESSAGE_EDGE_TYPE",
    "DEFAULT_FILE_BLOB_IDS",
    "RESPONSE_MESSAGE_TYPE",
    "DEBUG_HISTORY_TYPE",
    "RESPONSE_LOG_SUCCESS",
    "RESPONSE_LOG_FAILURE",
    "RESPONSE_LOG_ERROR",
]
