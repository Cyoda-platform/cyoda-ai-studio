"""Content builders for edge messages."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Constants for edge message entity types
MESSAGE_EDGE_TYPE = "flow_edge_message"
DEFAULT_FILE_BLOB_IDS: List[str] = []
RESPONSE_MESSAGE_TYPE = "ai"
DEBUG_HISTORY_TYPE = "streaming_debug_history"


class DebugHistoryData(BaseModel):
    """Debug history data structure."""

    type: str = DEBUG_HISTORY_TYPE
    timestamp: str
    events_count: int
    events: List[Dict[str, Any]]


class ResponseEdgeMessageContent(BaseModel):
    """Edge message content for response with history."""

    type: str = RESPONSE_MESSAGE_TYPE
    message: str
    conversation_id: str
    user_id: str
    timestamp: str
    metadata: Dict[str, Any]
    debug_history: DebugHistoryData


def build_edge_message_content(
    message_type: str,
    message_content: str,
    conversation_id: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]],
    file_blob_ids: Optional[List[str]],
) -> Dict[str, Any]:
    """Build edge message content dictionary.

    Args:
        message_type: Type of message
        message_content: Message content
        conversation_id: Conversation ID
        user_id: User ID
        metadata: Optional metadata
        file_blob_ids: Optional file attachments

    Returns:
        Edge message content dictionary
    """
    return {
        "type": message_type,
        "message": message_content,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
        "file_blob_ids": file_blob_ids or DEFAULT_FILE_BLOB_IDS,
    }


def build_edge_message_meta() -> Dict[str, Any]:
    """Build edge message metadata for Cyoda entity.

    Returns:
        Meta dictionary for entity service
    """
    from common.config.config import (
        CYODA_ENTITY_TYPE_EDGE_MESSAGE,
        ENTITY_VERSION,
    )

    return {
        "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE,
        "entity_model": MESSAGE_EDGE_TYPE,
        "entity_version": ENTITY_VERSION,
    }


def build_debug_history_content(
    conversation_id: str,
    user_id: str,
    streaming_events: List[Dict[str, Any]],
    response_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build debug history content dictionary.

    Args:
        conversation_id: Conversation ID
        user_id: User ID
        streaming_events: List of streaming events
        response_summary: Optional summary of the response

    Returns:
        Debug history content dictionary
    """
    return {
        "type": "streaming_debug_history",
        "conversation_id": conversation_id,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "events_count": len(streaming_events),
        "events": streaming_events,
        "response_summary": response_summary or {},
    }


def build_response_debug_history(
    streaming_events: List[Dict[str, Any]],
) -> DebugHistoryData:
    """Build debug history data structure for response.

    Args:
        streaming_events: List of streaming events

    Returns:
        DebugHistoryData object
    """
    return DebugHistoryData(
        timestamp=datetime.now(timezone.utc).isoformat(),
        events_count=len(streaming_events),
        events=streaming_events,
    )


def build_response_edge_message(
    conversation_id: str,
    user_id: str,
    response_content: str,
    metadata: Optional[Dict[str, Any]],
    debug_history: DebugHistoryData,
) -> ResponseEdgeMessageContent:
    """Build edge message content for response with history.

    Args:
        conversation_id: Conversation ID
        user_id: User ID
        response_content: AI response content
        metadata: Optional metadata
        debug_history: Debug history data

    Returns:
        ResponseEdgeMessageContent object
    """
    return ResponseEdgeMessageContent(
        message=response_content,
        conversation_id=conversation_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        metadata=metadata or {},
        debug_history=debug_history,
    )
