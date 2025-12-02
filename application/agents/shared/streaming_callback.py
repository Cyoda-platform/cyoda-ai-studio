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
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.run_config import StreamingMode
from google.genai import types

logger = logging.getLogger(__name__)


def accumulate_streaming_response(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Accumulate all text chunks from streaming events into a single response.

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
    """
    # Be defensive: older ADK versions may not expose run_config on CallbackContext.
    run_config = getattr(callback_context, "run_config", None)
    if run_config is None:
        invocation_context = getattr(callback_context, "_invocation_context", None)
        if invocation_context is not None:
            run_config = getattr(invocation_context, "run_config", None)

    streaming_mode = getattr(run_config, "streaming_mode", None) if run_config else None

    # If we know streaming_mode and it's explicitly not SSE, skip accumulation.
    if streaming_mode is not None and streaming_mode is not StreamingMode.SSE:
        logger.debug("Skipping accumulate_streaming_response: streaming_mode=%s", streaming_mode)
        return None

    chunks = []

    # Get the current invocation ID to filter events
    current_invocation_id = callback_context.invocation_id

    # Get events from the session
    events = callback_context.session.events

    # Collect all text chunks from model responses in the CURRENT invocation only.
    # Iterate in reverse to avoid scanning the entire session when there are many
    # previous invocations in the session history.
    found_current_invocation = False

    for event in reversed(events):
        # Filter by invocation_id to avoid accumulating from previous invocations
        if hasattr(event, "invocation_id") and event.invocation_id != current_invocation_id:
            if found_current_invocation:
                # We've already processed this invocation's events; stop scanning
                break
            continue

        found_current_invocation = True

        if hasattr(event, "content") and event.content:
            # Only process model responses (role='model')
            if hasattr(event.content, "role") and event.content.role == "model":
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text is not None:
                            chunks.append(part.text)

    # Restore chronological order (we iterated in reverse above)
    chunks.reverse()

    # Return accumulated content if we found any text
    if chunks:
        merged_text = "".join(chunks)
        logger.debug(
            "✅ Accumulated %s text chunks into %s characters (invocation: %s)",
            len(chunks),
            len(merged_text),
            current_invocation_id,
        )
        return types.Content(role="model", parts=[types.Part(text=merged_text)])

    logger.info(
        "⚠️ No text chunks found to accumulate (invocation: %s)",
        current_invocation_id,
    )
    return None

