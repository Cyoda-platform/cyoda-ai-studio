"""
Response Validation Callback for ensuring non-empty agent responses.

This callback ensures that agents always return meaningful responses to users,
preventing empty or whitespace-only responses that can occur when:
- Agent only calls tools without generating text
- Streaming ends with empty final event
- Agent completes without explicit response

Based on ADK callbacks documentation:
https://google.github.io/adk-docs/callbacks/types-of-callbacks/#after-agent-callback
"""

import logging
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

logger = logging.getLogger(__name__)


def ensure_non_empty_response(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Ensure agent response is not empty.

    This after_agent_callback checks if the agent produced any text response.
    If the response is empty or whitespace-only, it generates a default message.

    This is particularly useful when:
    - Agent only executes tools without generating explanatory text
    - Streaming mode results in empty final event
    - Agent completes task silently

    Args:
        callback_context: The callback context containing session and events

    Returns:
        Content with default message if response is empty, None otherwise
    """
    # Get events from the current invocation
    events = callback_context.session.events

    # Check if we have any text content from model responses
    has_text_response = False
    for event in events:
        if hasattr(event, "content") and event.content:
            # Only check model responses (role='model')
            if hasattr(event.content, "role") and event.content.role == "model":
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        # Check for non-empty text (excluding whitespace)
                        if hasattr(part, "text") and part.text and part.text.strip():
                            has_text_response = True
                            break
        if has_text_response:
            break

    # If no text response found, provide a default message
    if not has_text_response:
        logger.info("⚠️ No text response found - providing default message")
        return types.Content(
            role="model",
            parts=[types.Part(text="Task completed successfully.")]
        )

    # Response is valid, allow it to proceed
    return None


def ensure_non_empty_response_with_tool_summary(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Ensure agent response is not empty, with tool execution summary.

    Similar to ensure_non_empty_response, but when response is empty,
    it generates a summary of tools that were executed instead of a generic message.

    This provides better user experience by explaining what actions were taken.

    Args:
        callback_context: The callback context containing session and events

    Returns:
        Content with tool summary if response is empty, None otherwise
    """
    # Get events from the current invocation
    events = callback_context.session.events

    # Check if we have any text content from model responses
    has_text_response = False
    tool_calls = []

    for event in events:
        if hasattr(event, "content") and event.content:
            # Check model responses for text
            if hasattr(event.content, "role") and event.content.role == "model":
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        # Check for non-empty text
                        if hasattr(part, "text") and part.text and part.text.strip():
                            has_text_response = True
                        # Track tool calls
                        if hasattr(part, "function_call") and part.function_call:
                            tool_calls.append(part.function_call.name)

    # If no text response found, provide a summary
    if not has_text_response:
        if tool_calls:
            # Generate summary of tools executed
            unique_tools = list(dict.fromkeys(tool_calls))  # Preserve order, remove duplicates
            if len(unique_tools) == 1:
                message = f"Executed {unique_tools[0]} successfully."
            else:
                tools_list = ", ".join(unique_tools[:-1]) + f" and {unique_tools[-1]}"
                message = f"Executed the following tools: {tools_list}."
            
            logger.info(f"⚠️ No text response found - providing tool summary: {message}")
            return types.Content(
                role="model",
                parts=[types.Part(text=message)]
            )
        else:
            # No tools and no text - generic message
            logger.info("⚠️ No text response or tools found - providing default message")
            return types.Content(
                role="model",
                parts=[types.Part(text="Task completed successfully.")]
            )

    # Response is valid, allow it to proceed
    return None


def extract_hook_from_state(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Extract hook from session state and include it in the response.

    This callback checks if tools have stored a hook in session state
    (e.g., last_tool_hook) and ensures it's properly included in the
    agent's final response.

    This is useful for UI integration where tools need to trigger
    specific UI actions (like refreshing canvas, showing notifications, etc.).

    Note: This callback doesn't modify the response text, it just ensures
    hooks are properly propagated. The actual hook extraction happens in
    StreamingService.

    Args:
        callback_context: The callback context containing session state

    Returns:
        None (hooks are handled via session state, not response content)
    """
    # Check if there's a hook in session state
    hook = callback_context.state.get("last_tool_hook")
    
    if hook:
        logger.info(f"🎣 Hook found in session state: {hook.get('type', 'unknown')}")
        # Hook will be extracted by StreamingService from session state
        # We don't need to modify the response content here
    
    # Return None to allow normal response flow
    return None

