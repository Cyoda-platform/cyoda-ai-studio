"""
Streaming callback for accumulating streaming responses in multi-agent systems.

This callback addresses the issue where the default AgentTool.run_async() only keeps
the last event's content, which is problematic when StreamingMode.SSE is enabled because
the last event often has parts=None or empty text (the final "done" event), discarding
all previous streaming chunks.

Based on ADK documentation:
https://google.github.io/adk-docs/callbacks/types-of-callbacks/#after-agent-callback
"""

import logging
from typing import Any, List, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.run_config import StreamingMode
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Streaming callback constants
STREAMING_MODE_DEBUG = "Skipping accumulate_streaming_response: streaming_mode=%s"
ACCUMULATION_SUCCESS_LOG = (
    "✅ Accumulated %s text chunks into %s characters (invocation: %s)"
)
ACCUMULATION_EMPTY_LOG = "⚠️ No text chunks found to accumulate (invocation: %s)"
MODEL_ROLE = "model"


class StreamingEvent(BaseModel):
    """Streaming event metadata."""

    invocation_id: str
    has_content: bool
    chunks_count: int = 0
    total_length: int = 0


class AccumulationResult(BaseModel):
    """Result of streaming accumulation."""

    success: bool
    chunks_count: int = 0
    total_length: int = 0
    content: Optional[Any] = None


def _get_streaming_mode(callback_context: CallbackContext) -> Optional[StreamingMode]:
    """Extract streaming mode from callback context.

    Args:
        callback_context: The callback context

    Returns:
        StreamingMode if found, None otherwise
    """
    run_config = getattr(callback_context, "run_config", None)
    if run_config is None:
        invocation_context = getattr(callback_context, "_invocation_context", None)
        if invocation_context is not None:
            run_config = getattr(invocation_context, "run_config", None)

    return getattr(run_config, "streaming_mode", None) if run_config else None


def _should_skip_accumulation(streaming_mode: Optional[StreamingMode]) -> bool:
    """Determine if accumulation should be skipped based on streaming mode.

    Args:
        streaming_mode: The streaming mode from configuration

    Returns:
        True if accumulation should be skipped, False otherwise
    """
    if streaming_mode is not None and streaming_mode is not StreamingMode.SSE:
        logger.debug(STREAMING_MODE_DEBUG, streaming_mode)
        return True
    return False


def _extract_text_chunks(events: List[Any], current_invocation_id: str) -> List[str]:
    """Extract all text chunks from events for current invocation.

    Args:
        events: List of events from session
        current_invocation_id: Current invocation ID to filter events

    Returns:
        List of text chunks in chronological order
    """
    chunks = []
    found_current_invocation = False

    # Iterate in reverse to stop scanning early when many previous invocations exist
    for event in reversed(events):
        # Filter by invocation_id to avoid accumulating from previous invocations
        if (
            hasattr(event, "invocation_id")
            and event.invocation_id != current_invocation_id
        ):
            if found_current_invocation:
                break
            continue

        found_current_invocation = True

        if hasattr(event, "content") and event.content:
            # Only process model responses
            if hasattr(event.content, "role") and event.content.role == MODEL_ROLE:
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text is not None:
                            chunks.append(part.text)

    # Restore chronological order (we iterated in reverse)
    chunks.reverse()
    return chunks


def _build_accumulated_content(chunks: List[str]) -> types.Content:
    """Build Content object from accumulated text chunks.

    Args:
        chunks: List of text chunks to merge

    Returns:
        Content object with merged text
    """
    merged_text = "".join(chunks)
    return types.Content(role=MODEL_ROLE, parts=[types.Part(text=merged_text)])


def accumulate_streaming_response(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Accumulate all text chunks from streaming events into a single response.

    This callback is designed to work with StreamingMode.SSE where the LLM
    generates multiple partial events followed by a final event. The default
    AgentTool implementation only keeps the last event's content, which often
    has parts=None, losing all the streamed text chunks.

    This callback:
    1. Collects all text chunks from the CURRENT invocation only
    2. Merges them into a single complete response
    3. Returns the accumulated content

    Args:
        callback_context: The callback context containing session and events

    Returns:
        Content with accumulated text, or None if no text was found

    Example:
        >>> result = accumulate_streaming_response(callback_context)
        >>> if result:
        ...     print(result.parts[0].text)
    """
    # Step 1: Extract streaming mode
    streaming_mode = _get_streaming_mode(callback_context)

    # Step 2: Check if accumulation should be skipped
    if _should_skip_accumulation(streaming_mode):
        return None

    # Step 3: Get current invocation ID and session events
    current_invocation_id = callback_context.invocation_id
    events = callback_context.session.events

    # Step 4: Extract text chunks from current invocation
    chunks = _extract_text_chunks(events, current_invocation_id)

    # Step 5: Return result if chunks found
    if chunks:
        merged_text_len = sum(len(chunk) for chunk in chunks)
        logger.debug(
            ACCUMULATION_SUCCESS_LOG,
            len(chunks),
            merged_text_len,
            current_invocation_id,
        )
        return _build_accumulated_content(chunks)

    # Step 6: Log empty result
    logger.info(ACCUMULATION_EMPTY_LOG, current_invocation_id)
    return None
