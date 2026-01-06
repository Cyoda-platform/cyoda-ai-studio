"""Conversation history sanitizer for LLM compatibility.

Validates and sanitizes conversation history to ensure it meets LLM API requirements,
particularly for OpenAI's requirement that assistant messages with tool_calls must be
followed by corresponding tool response messages.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def sanitize_conversation_history(
    conversation_history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Sanitize conversation history to prevent incomplete tool call sequences.

    OpenAI API requires that any assistant message with 'tool_calls' must be followed
    by tool messages responding to each 'tool_call_id'. This function validates and
    sanitizes the conversation history to ensure this requirement is met.

    Args:
        conversation_history: List of conversation message dictionaries

    Returns:
        Sanitized list of conversation messages
    """
    logger.info(f"Sanitizing conversation history with {len(conversation_history)} messages")

    # DEBUG: Log message structures
    if conversation_history:
        logger.info(f"First message keys: {list(conversation_history[0].keys())}")
        logger.info(f"First message type: {conversation_history[0].get('type', 'NO_TYPE')}")

        # Look for AI messages to understand structure
        for idx, msg in enumerate(conversation_history[:min(50, len(conversation_history))]):
            if msg.get('type') == 'ai' or msg.get('type') == 'question':
                inner_msg = msg.get('message')
                if inner_msg and isinstance(inner_msg, dict):
                    if 'tool_calls' in inner_msg:
                        logger.warning(f"Found AI message with tool_calls at index {idx}: {inner_msg.get('tool_calls', [])[:1]}")
                    logger.info(f"AI message at {idx} has keys: {list(inner_msg.keys()) if isinstance(inner_msg, dict) else 'NOT_DICT'}")
                else:
                    logger.info(f"AI message at {idx} has message type: {type(inner_msg)}")

    if not conversation_history:
        logger.info("Conversation history is empty, returning empty list")
        return []

    sanitized = []
    i = 0

    while i < len(conversation_history):
        message = conversation_history[i]

        # Check if this is an assistant message with tool calls
        if _has_tool_calls(message):
            logger.debug(f"Found message with tool_calls at index {i}")
            tool_call_ids = _extract_tool_call_ids(message)
            logger.debug(f"Extracted tool_call_ids: {tool_call_ids}")

            if not tool_call_ids:
                # No tool_call_ids found, but has tool_calls structure
                # This is malformed, skip this message
                logger.warning(
                    f"Skipping assistant message at index {i}: has tool_calls but no tool_call_ids"
                )
                i += 1
                continue

            # Look ahead for tool response messages
            tool_responses_found = _find_tool_responses(
                conversation_history, i + 1, tool_call_ids
            )

            if tool_responses_found:
                # Valid sequence: add the assistant message
                sanitized.append(message)
                i += 1
            else:
                # Invalid sequence: truncate history here
                logger.warning(
                    f"Truncating conversation history at index {i}: "
                    f"assistant message has tool_calls {tool_call_ids} but no matching tool responses found"
                )
                # Stop processing and return what we have so far
                break
        else:
            # Regular message (user, assistant without tool calls, tool response)
            sanitized.append(message)
            i += 1

    if len(sanitized) < len(conversation_history):
        logger.info(
            f"Conversation history sanitized: {len(conversation_history)} -> {len(sanitized)} messages"
        )

    return sanitized


def _has_tool_calls(message: Dict[str, Any]) -> bool:
    """Check if a message has tool calls.

    Args:
        message: Message dictionary

    Returns:
        True if message has tool_calls
    """
    # Check for different possible structures
    if isinstance(message, dict):
        # Check if it's an edge message structure with a nested 'message'
        if "message" in message and isinstance(message["message"], dict):
            inner_message = message["message"]
            if "tool_calls" in inner_message and inner_message["tool_calls"]:
                return True

        # Check direct structure
        if "tool_calls" in message and message["tool_calls"]:
            return True

    return False


def _extract_tool_call_ids(message: Dict[str, Any]) -> List[str]:
    """Extract tool_call_ids from an assistant message.

    Args:
        message: Assistant message with tool calls

    Returns:
        List of tool_call_ids
    """
    tool_call_ids = []

    # Try nested structure first
    if "message" in message and isinstance(message["message"], dict):
        inner_message = message["message"]
        tool_calls = inner_message.get("tool_calls", [])
    else:
        tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        return []

    for tool_call in tool_calls:
        if isinstance(tool_call, dict) and "id" in tool_call:
            tool_call_ids.append(tool_call["id"])

    return tool_call_ids


def _find_tool_responses(
    conversation_history: List[Dict[str, Any]],
    start_index: int,
    required_tool_call_ids: List[str],
) -> bool:
    """Check if tool response messages exist for all required tool_call_ids.

    Args:
        conversation_history: Full conversation history
        start_index: Index to start searching from
        required_tool_call_ids: List of tool_call_ids that need responses

    Returns:
        True if all required tool responses are found
    """
    found_tool_call_ids = set()

    # Search forward from start_index
    for i in range(start_index, len(conversation_history)):
        msg = conversation_history[i]

        # Check if it's a tool response message
        tool_call_id = _get_tool_call_id_from_response(msg)
        if tool_call_id:
            found_tool_call_ids.add(tool_call_id)

        # If we hit another assistant message, stop searching
        # (tool responses must come immediately after the assistant message with tool_calls)
        if _is_assistant_message(msg) and i != start_index:
            break

    # Check if all required tool_call_ids were found
    required_set = set(required_tool_call_ids)
    return required_set.issubset(found_tool_call_ids)


def _get_tool_call_id_from_response(message: Dict[str, Any]) -> Optional[str]:
    """Extract tool_call_id from a tool response message.

    Args:
        message: Potential tool response message

    Returns:
        tool_call_id if found, None otherwise
    """
    # Check nested structure
    if "message" in message and isinstance(message["message"], dict):
        inner_message = message["message"]
        if "tool_call_id" in inner_message:
            return inner_message["tool_call_id"]

    # Check direct structure
    if "tool_call_id" in message:
        return message["tool_call_id"]

    return None


def _is_assistant_message(message: Dict[str, Any]) -> bool:
    """Check if a message is from the assistant.

    Args:
        message: Message dictionary

    Returns:
        True if message is from assistant
    """
    # Check nested structure
    if "message" in message and isinstance(message["message"], dict):
        inner_message = message["message"]
        role = inner_message.get("role")
        if role == "assistant":
            return True

    # Check direct structure
    role = message.get("role")
    if role == "assistant":
        return True

    # Check type field (alternative structure)
    msg_type = message.get("type")
    if msg_type in ["ai", "question"]:
        return True

    return False


__all__ = ["sanitize_conversation_history"]
