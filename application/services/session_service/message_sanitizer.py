"""ADK Session message sanitizer for OpenAI tool call validation.

Sanitizes ADK session events to prevent incomplete tool call sequences
that would cause OpenAI API errors.
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def sanitize_adk_session_events(events: List[Any]) -> List[Any]:
    """Sanitize ADK session events to remove incomplete tool call sequences.

    OpenAI requires that assistant messages with 'tool_calls' must be followed
    by tool response messages for each tool_call_id. This function validates
    and sanitizes ADK session events to ensure this requirement.

    Args:
        events: List of ADK Event objects

    Returns:
        Sanitized list of events with incomplete tool call sequences removed
    """
    if not events:
        return []

    # Extract messages from events
    try:
        # ADK stores messages in the event history
        # We need to validate the message sequence
        sanitized_events = []
        pending_tool_calls = {}  # tool_call_id -> event_index mapping

        for idx, event in enumerate(events):
            # Check if event has content with messages
            if not hasattr(event, "content") or not event.content:
                sanitized_events.append(event)
                continue

            # Check if content has parts (ADK message structure)
            if not hasattr(event.content, "parts") or not event.content.parts:
                sanitized_events.append(event)
                continue

            # Scan parts for tool calls and responses
            has_tool_call = False
            has_tool_response = False
            tool_call_ids_in_event = []
            tool_response_ids_in_event = []

            for part in event.content.parts:
                # Check for function_call (tool call)
                if hasattr(part, "function_call") and part.function_call:
                    has_tool_call = True
                    call_id = getattr(part.function_call, "id", None)
                    if call_id:
                        tool_call_ids_in_event.append(call_id)
                        pending_tool_calls[call_id] = idx

                # Check for function_response (tool response)
                if hasattr(part, "function_response") and part.function_response:
                    has_tool_response = True
                    response_id = getattr(part.function_response, "id", None)
                    if response_id and response_id in pending_tool_calls:
                        tool_response_ids_in_event.append(response_id)
                        # Remove from pending
                        del pending_tool_calls[response_id]

            # Add event to sanitized list
            sanitized_events.append(event)

        # If there are pending tool calls without responses, truncate
        if pending_tool_calls:
            # Find the earliest incomplete tool call
            earliest_incomplete_idx = min(pending_tool_calls.values())
            logger.warning(
                f"Found {len(pending_tool_calls)} incomplete tool calls in session events. "
                f"Truncating from event index {earliest_incomplete_idx}. "
                f"Tool call IDs: {list(pending_tool_calls.keys())}"
            )
            sanitized_events = sanitized_events[:earliest_incomplete_idx]
            logger.info(
                f"Session events sanitized: {len(events)} -> {len(sanitized_events)}"
            )

        return sanitized_events

    except Exception as e:
        logger.error(f"Error during ADK session sanitization: {e}", exc_info=True)
        # On error, return original events to avoid breaking the session
        return events


__all__ = ["sanitize_adk_session_events"]
