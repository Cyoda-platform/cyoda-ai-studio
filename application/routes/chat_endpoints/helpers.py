"""Shared helper functions for chat endpoints."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List

from quart import Response

from application.entity.conversation import Conversation
from application.services.openai.canvas_question_service import CanvasQuestionService
from application.services.service_factory import get_service_factory
from services.services import get_cyoda_assistant, get_repository

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Enable debug logging for helpers


def get_chat_service():
    """Get ChatService instance."""
    return get_service_factory().chat_service


def get_chat_stream_service():
    """Get ChatStreamService instance."""
    return get_service_factory().chat_stream_service


def get_canvas_question_service(google_adk_service: Any) -> CanvasQuestionService:
    """Get CanvasQuestionService instance."""
    return CanvasQuestionService(google_adk_service)


def get_cyoda_assistant_instance() -> Any:
    """Get the Cyoda Assistant instance."""
    return get_cyoda_assistant()


async def get_conversation(technical_id: str):
    """Get conversation by ID."""
    service = get_chat_service()
    return await service.get_conversation(technical_id)


async def update_conversation(conversation: Conversation):
    """Update conversation."""
    service = get_chat_service()
    return await service.update_conversation(conversation)


def get_edge_message_persistence_service():
    """Get edge message persistence service."""
    from application.services.edge_message_persistence_service import (
        EdgeMessagePersistenceService,
    )

    repository = get_repository()
    return EdgeMessagePersistenceService(repository)


def error_response(error_message: str) -> Response:
    """Create an error SSE response."""

    async def error_stream():
        yield f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"

    return Response(error_stream(), mimetype="text/event-stream")


def build_message_to_process(user_message: str, file_blob_ids: List[str]) -> str:
    """Build the message to process with file attachment info."""
    if file_blob_ids:
        return f"{user_message} (with {len(file_blob_ids)} attached file(s))"
    return user_message


def build_stream_response(event_gen: AsyncGenerator[str, None]) -> Response:
    """Build SSE response with proper headers."""
    return Response(
        event_gen,
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Encoding": "none",
        },
    )


def process_content_event(
    sse_event: str, accumulated_response: str, streaming_events: List[Dict[str, Any]]
) -> tuple[str, List[Dict[str, Any]]]:
    """Process a content event from the stream."""
    try:
        data_start = sse_event.find("data: ") + 6
        json_str = sse_event[data_start:].strip()
        event_data = json.loads(json_str)

        # The streaming service sends 'chunk' field, not 'content'
        content_chunk = event_data.get("chunk") or event_data.get("content")

        if content_chunk:
            logger.debug(f"📝 [helper] Extracting content chunk: '{content_chunk[:50]}...' (length: {len(content_chunk)})")
            accumulated_response += content_chunk
            logger.debug(f"📝 [helper] New accumulated length: {len(accumulated_response)}")
        else:
            logger.warning(f"⚠️ [helper] Content event has no 'chunk' or 'content' field: {event_data}")

        # Store the full event data for debugging/timeline display
        streaming_events.append(
            {
                "type": "content",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": event_data
            }
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse content event: {e}")
        logger.debug(f"Failed event data: {sse_event[:200]}")

    return accumulated_response, streaming_events


def process_done_event(
    sse_event: str, accumulated_response: str, streaming_events: List[Dict[str, Any]]
) -> tuple[bool, str | None, str, str | None, Dict[str, Any] | None, List[Dict[str, Any]]]:
    """Process a done event from the stream."""
    done_event_sent = True
    done_event_to_send = None
    adk_session_id_result = None
    hook_result = None

    try:
        data_start = sse_event.find("data: ") + 6
        json_str = sse_event[data_start:].strip()
        event_data = json.loads(json_str)

        if "adk_session_id" in event_data:
            adk_session_id_result = event_data["adk_session_id"]
        if "hook" in event_data:
            hook_result = event_data["hook"]

        done_event_to_send = sse_event
        # Store the full event data for debugging/timeline display
        streaming_events.append(
            {
                "type": "done",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": event_data
            }
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse done event: {e}")

    return (
        done_event_sent,
        done_event_to_send,
        accumulated_response,
        adk_session_id_result,
        hook_result,
        streaming_events,
    )


def get_event_type(sse_event: str) -> str:
    """Determine event type from SSE event string."""
    if "event: " in sse_event:
        event_line = [line for line in sse_event.split("\n") if line.startswith("event: ")]
        if event_line:
            return event_line[0].replace("event: ", "").strip()
    return "unknown"
