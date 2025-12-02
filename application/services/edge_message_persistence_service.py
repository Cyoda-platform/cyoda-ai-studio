"""
Edge Message Persistence Service

Handles saving conversation messages and streaming debug history as edge messages
to avoid data corruption and ensure reliable persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EdgeMessagePersistenceService:
    """Service for persisting messages as edge messages."""

    def __init__(self, repository: Any):
        """
        Initialize the persistence service.

        Args:
            repository: The Cyoda repository for saving edge messages
        """
        self.repository = repository

    async def save_message_as_edge_message(
        self,
        message_type: str,
        message_content: str,
        conversation_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        file_blob_ids: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Save a message as an edge message.

        Args:
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
            edge_message_content = {
                "type": message_type,
                "message": message_content,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
                "file_blob_ids": file_blob_ids or [],
            }

            from common.config.config import (
                CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                ENTITY_VERSION,
            )

            meta = {
                "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                "entity_model": "flow_edge_message",
                "entity_version": ENTITY_VERSION,
            }

            edge_message_id = await self.repository.save(
                meta=meta, entity=edge_message_content
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

    async def save_streaming_debug_history(
        self,
        conversation_id: str,
        user_id: str,
        streaming_events: List[Dict[str, Any]],
        response_summary: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Save streaming debug history as an edge message.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID
            streaming_events: List of streaming events from the stream
            response_summary: Optional summary of the response

        Returns:
            Edge message ID if successful, None otherwise
        """
        try:
            debug_history = {
                "type": "streaming_debug_history",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events_count": len(streaming_events),
                "events": streaming_events,
                "response_summary": response_summary or {},
            }

            from common.config.config import (
                CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                ENTITY_VERSION,
            )

            meta = {
                "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                "entity_model": "flow_edge_message",
                "entity_version": ENTITY_VERSION,
            }

            edge_message_id = await self.repository.save(
                meta=meta, entity=debug_history
            )

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
        self,
        conversation_id: str,
        user_id: str,
        response_content: str,
        streaming_events: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Save response with streaming debug history in a single edge message.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID
            response_content: The AI response content
            streaming_events: List of streaming events
            metadata: Optional metadata (hooks, etc.)

        Returns:
            Edge message ID if successful, None otherwise
        """
        try:
            debug_history = {
                "type": "streaming_debug_history",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events_count": len(streaming_events),
                "events": streaming_events,
            }

            edge_message_content = {
                "type": "ai",
                "message": response_content,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
                "debug_history": debug_history,
            }

            from common.config.config import (
                CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                ENTITY_VERSION,
            )

            meta = {
                "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                "entity_model": "flow_edge_message",
                "entity_version": ENTITY_VERSION,
            }

            edge_message_id = await self.repository.save(
                meta=meta, entity=edge_message_content
            )

            if edge_message_id:
                logger.info(
                    f"✅ Saved response with debug history as edge message {edge_message_id}"
                )
                return edge_message_id

            logger.error("Failed to save response with debug history")
            return None

        except Exception as e:
            logger.error(f"❌ Error saving response with debug history: {e}")
            return None
