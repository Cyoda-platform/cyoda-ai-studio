"""Stream chat endpoint."""

import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from quart import Blueprint, Response, request
from quart_rate_limiter import rate_limit

from application.entity.conversation import Conversation
from application.routes.chat_endpoints.helpers import (
    build_message_to_process,
    build_stream_response,
    error_response,
    get_chat_service,
    get_cyoda_assistant_instance,
    get_edge_message_persistence_service,
    get_event_type,
    process_content_event,
    process_done_event,
    update_conversation,
)
from application.routes.common.auth import get_authenticated_user
from application.routes.common.rate_limiting import default_rate_limit_key
from application.services.streaming_service import StreamingService
from application.services.streaming.conversation_sanitizer import (
    sanitize_conversation_history,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Enable debug logging for stream endpoint

stream_bp = Blueprint("chat_stream", __name__)


async def _get_conversation(technical_id: str):
    """Get conversation by ID."""
    service = get_chat_service()
    return await service.get_conversation(technical_id)


async def _save_user_message_to_conversation(
    technical_id: str, user_id: str, user_message: str, file_blob_ids: List[str], conversation: Conversation
) -> tuple[str, Conversation]:
    """Save user message to conversation and return edge message ID."""
    persistence_service = get_edge_message_persistence_service()
    user_message_edge_id = await persistence_service.save_message_as_edge_message(
        message_type="user",
        message_content=user_message,
        conversation_id=technical_id,
        user_id=user_id,
        file_blob_ids=file_blob_ids if file_blob_ids else None,
    )
    logger.info(f"✅ User message saved as edge message: {user_message_edge_id}")

    conversation.add_message("user", user_message_edge_id, file_blob_ids if file_blob_ids else None)

    if file_blob_ids:
        if conversation.file_blob_ids is None:
            conversation.file_blob_ids = []
        for file_id in file_blob_ids:
            if file_id not in conversation.file_blob_ids:
                conversation.file_blob_ids.append(file_id)

    conversation = await update_conversation(conversation)
    return user_message_edge_id, conversation


async def _save_file_as_edge_message(
    file_storage,
    filename: str,
    file_content: bytes,
    conversation_id: str,
    user_id: str
) -> Optional[str]:
    """Save uploaded file as an edge message.

    Args:
        file_storage: File storage object from request
        filename: Original filename
        file_content: File content as bytes
        conversation_id: Conversation technical ID
        user_id: User ID

    Returns:
        Edge message ID (blob_id) if successful, None otherwise
    """
    from application.routes.chat_endpoints.helpers import get_edge_message_persistence_service

    try:
        # Encode file content as base64
        base64_content = base64.b64encode(file_content).decode('utf-8')

        # Prepare metadata with filename and encoding
        metadata = {
            "filename": filename,
            "encoding": "base64",
            "content_type": file_storage.content_type or "application/octet-stream"
        }

        # Save as edge message
        edge_service = get_edge_message_persistence_service()
        blob_id = await edge_service.save_message_as_edge_message(
            message_type="file",
            message_content=base64_content,
            conversation_id=conversation_id,
            user_id=user_id,
            metadata=metadata,
            file_blob_ids=None
        )

        if blob_id:
            logger.info(f"✅ File '{filename}' saved as edge message: {blob_id}")
        else:
            logger.error(f"❌ Failed to save file '{filename}' as edge message")

        return blob_id

    except Exception as e:
        logger.error(f"❌ Error saving file '{filename}': {e}", exc_info=True)
        return None


async def _parse_stream_request(
    technical_id: str,
    user_id: str
) -> tuple[str, List[str], Optional[str]]:
    """Parse stream request for message, file blob IDs, and adk_session_id.

    Handles both JSON requests (for messages without files) and FormData requests
    (for messages with file attachments).

    Args:
        technical_id: Conversation technical ID
        user_id: User ID

    Returns:
        Tuple of (user_message, file_blob_ids, adk_session_id)
    """
    file_blob_ids = []

    # Check if request contains files (FormData)
    files = await request.files
    if files and 'files' in files:
        # FormData request - parse form fields
        form = await request.form
        user_message = form.get("message", "").strip()
        adk_session_id = form.get("adk_session_id")

        # Process uploaded files
        uploaded_files = files.getlist('files')
        logger.info(f"📎 Received {len(uploaded_files)} file(s) via FormData")

        # Save each file as an edge message
        for file_storage in uploaded_files:
            filename = file_storage.filename or f"file_{uuid.uuid4().hex[:8]}.txt"
            file_content = file_storage.read()

            # Save file and get blob ID
            blob_id = await _save_file_as_edge_message(
                file_storage,
                filename,
                file_content,
                technical_id,
                user_id
            )

            if blob_id:
                file_blob_ids.append(blob_id)
                logger.info(f"📎 File '{filename}' → blob_id: {blob_id}")
            else:
                logger.warning(f"⚠️ Failed to save file '{filename}'")
    else:
        # JSON request - parse JSON body
        data = await request.get_json()
        if data is None:
            raise ValueError("Request body must be either JSON or FormData")

        user_message = data.get("message", "").strip()
        file_blob_ids = data.get("file_blob_ids", [])
        adk_session_id = data.get("adk_session_id")

    if not isinstance(file_blob_ids, list):
        raise ValueError("file_blob_ids must be a list")

    logger.info(f"📋 Parsed request: message='{user_message[:50]}...', files={len(file_blob_ids)}, session={adk_session_id}")

    return user_message, file_blob_ids, adk_session_id


def _create_streaming_generator(
    technical_id: str,
    user_id: str,
    conversation: Conversation,
    assistant: Any,
    message_to_process: str
):
    """Create streaming generator from service.

    Args:
        technical_id: Conversation technical ID.
        user_id: User ID.
        conversation: Conversation object.
        assistant: Assistant instance.
        message_to_process: Message to process.

    Returns:
        Streaming generator from service.
    """
    # Sanitize conversation history to prevent incomplete tool call sequences
    sanitized_history = sanitize_conversation_history(conversation.messages)

    return StreamingService.stream_agent_response(
        agent_wrapper=assistant,
        user_message=message_to_process,
        conversation_history=sanitized_history,
        conversation_id=technical_id,
        adk_session_id=conversation.adk_session_id,
        user_id=user_id,
    )


async def _process_streaming_event(
    sse_event: str,
    accumulated_response: str,
    streaming_events: List[Dict],
    done_event_sent: bool
) -> tuple[str, List[Dict], bool, Optional[str], Optional[str], Optional[Dict]]:
    """Process individual streaming event.

    Args:
        sse_event: SSE event string.
        accumulated_response: Accumulated response so far.
        streaming_events: List of streaming events.
        done_event_sent: Whether done event was sent.

    Returns:
        Tuple of (accumulated_response, streaming_events, done_event_sent, done_event_to_send, adk_session_id_result, hook_result).
    """
    done_event_to_send = None
    hook_result = None
    adk_session_id_result = None

    if "event: content" in sse_event:
        accumulated_response, streaming_events = process_content_event(
            sse_event, accumulated_response, streaming_events
        )
    elif "event: done" in sse_event:
        (
            done_event_sent,
            done_event_to_send,
            accumulated_response,
            adk_session_id_result,
            hook_result,
            streaming_events,
        ) = process_done_event(sse_event, accumulated_response, streaming_events)
    else:
        # Capture other event types (tool calls, thinking, etc.)
        try:
            event_type = get_event_type(sse_event)
            data_start = sse_event.find("data: ") + 6
            if data_start > 6:
                json_str = sse_event[data_start:].strip()
                event_data = json.loads(json_str)
                streaming_events.append({
                    "type": event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": event_data
                })
            else:
                streaming_events.append({
                    "type": event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        except (json.JSONDecodeError, ValueError):
            streaming_events.append({
                "type": "other",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    return accumulated_response, streaming_events, done_event_sent, done_event_to_send, adk_session_id_result, hook_result


def _build_fallback_done_event(accumulated_response: str, stream_error: Optional[str]) -> str:
    """Build fallback done event if not sent by service.

    Args:
        accumulated_response: Final accumulated response.
        stream_error: Stream error if any.

    Returns:
        SSE done event string.
    """
    done_data = {"message": "Stream completed", "response": accumulated_response}
    if stream_error:
        done_data["error"] = stream_error
    return f"event: done\ndata: {json.dumps(done_data)}\n\n"


def _create_stream_event_generator(
    technical_id: str,
    user_id: str,
    conversation: Conversation,
    assistant: Any,
    message_to_process: str,
) -> AsyncGenerator[str, None]:
    """Create the SSE event generator for streaming responses."""

    async def event_generator():
        accumulated_response = ""
        adk_session_id_result = None
        hook_result = None
        done_event_sent = False
        done_event_to_send = None
        stream_error = None
        streaming_events = []

        try:
            # Create streaming generator
            streaming_generator = _create_streaming_generator(
                technical_id, user_id, conversation, assistant, message_to_process
            )

            # Process events
            async for sse_event in streaming_generator:
                if "event: done" in sse_event:
                    logger.info(f"📤 [route] Received done event from upstream")
                if "event: content" in sse_event:
                    logger.debug(f"📝 [route] Received content event, current accumulated length: {len(accumulated_response)}")

                result = await _process_streaming_event(
                    sse_event, accumulated_response, streaming_events, done_event_sent
                )
                accumulated_response, streaming_events, done_event_sent, done_event_to_send, adk_session_id_result, hook_result = result

                if "event: content" in sse_event:
                    logger.debug(f"📝 [route] After processing, accumulated length: {len(accumulated_response)}")
                if "event: done" in sse_event:
                    logger.info(f"📤 [route] Yielding done event to client")
                yield sse_event

        except Exception as e:
            stream_error = str(e)
            logger.error(f"Error in stream generator: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': stream_error})}\n\n"

        finally:
            # Finalize stream
            await _finalize_stream(
                technical_id, user_id, accumulated_response, streaming_events,
                hook_result, adk_session_id_result, done_event_to_send,
                done_event_sent, stream_error
            )

            # Send done event only if it wasn't already sent
            if not done_event_sent:
                logger.warning("Done event was not sent by streaming service, sending fallback now")
                fallback = _build_fallback_done_event(accumulated_response, stream_error)
                logger.info(f"📤 [route finalize] Yielding fallback done event")
                yield fallback
            else:
                logger.info(f"📤 [route finalize] Done event already sent, not yielding again")

    return event_generator()


async def _finalize_stream(
    technical_id: str,
    user_id: str,
    accumulated_response: str,
    streaming_events: List[Dict[str, Any]],
    hook_result: Optional[Dict[str, Any]],
    adk_session_id_result: Optional[str],
    done_event_to_send: Optional[str],
    done_event_sent: bool,
    stream_error: Optional[str],
) -> None:
    """Finalize the stream by saving response and updating conversation."""
    logger.info(f"🔄 FINALLY BLOCK - accumulated_response length: {len(accumulated_response)}")
    try:
        if accumulated_response and accumulated_response.strip():
            persistence_service = get_edge_message_persistence_service()
            response_edge_message_id = await persistence_service.save_response_with_history(
                conversation_id=technical_id,
                user_id=user_id,
                response_content=accumulated_response,
                streaming_events=streaming_events,
                metadata={"hook": hook_result} if hook_result else None,
            )
            logger.info(f"✅ Response saved as edge message: {response_edge_message_id}")

            fresh_conversation = await _get_conversation(technical_id)
            if fresh_conversation:
                message_metadata = {"hook": hook_result} if hook_result else None
                fresh_conversation.add_message("ai", response_edge_message_id, metadata=message_metadata)

                if not fresh_conversation.adk_session_id and adk_session_id_result:
                    fresh_conversation.adk_session_id = adk_session_id_result

                await update_conversation(fresh_conversation)
                logger.info("✅ Conversation saved")
    except Exception as post_error:
        logger.error(f"Error in post-processing: {post_error}", exc_info=True)


@stream_bp.route("/<technical_id>/stream", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def stream_chat_message(technical_id: str) -> Response:
    """Stream AI response in real-time using Server-Sent Events (SSE)."""
    try:
        user_id, is_superuser = await get_authenticated_user()
        logger.info(f"Stream chat message - user_id: {user_id}, conversation_id: {technical_id}")

        conversation = await _get_conversation(technical_id)
        if not conversation:
            return error_response("Chat not found")

        if not is_superuser and conversation.user_id != user_id:
            return error_response("Access denied")

        try:
            user_message, file_blob_ids, adk_session_id = await _parse_stream_request(technical_id, user_id)
        except ValueError as e:
            return error_response(str(e))

        if not user_message:
            return error_response("Message is required")

        # Update conversation with adk_session_id if provided
        if adk_session_id and not conversation.adk_session_id:
            logger.info(f"Setting adk_session_id on conversation: {adk_session_id}")
            conversation.adk_session_id = adk_session_id
            conversation = await update_conversation(conversation)

        _, conversation = await _save_user_message_to_conversation(
            technical_id, user_id, user_message, file_blob_ids, conversation
        )

        assistant = get_cyoda_assistant_instance()
        message_to_process = build_message_to_process(user_message, file_blob_ids)
        event_gen = _create_stream_event_generator(technical_id, user_id, conversation, assistant, message_to_process)

        return build_stream_response(event_gen)

    except Exception as stream_error:
        logger.exception(f"Error setting up stream: {stream_error}")
        return error_response(str(stream_error))
