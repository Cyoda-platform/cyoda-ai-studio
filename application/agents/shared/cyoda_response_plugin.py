"""
Cyoda Response Plugin for ensuring quality agent responses.

This plugin provides:
1. Non-empty response validation
2. Hook extraction and propagation
3. Response enhancement with tool summaries

Based on ADK BasePlugin pattern:
https://google.github.io/adk-docs/callbacks/
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

logger = logging.getLogger(__name__)

# Constants
MODEL_ROLE = "model"
HOOK_STATE_KEY = "last_tool_hook"
DEFAULT_SUCCESS_MESSAGE = "Task completed successfully."


def has_text_content(part: types.Part) -> bool:
    """Check if a part contains non-empty text.

    Args:
        part: The part to check

    Returns:
        True if part has non-empty text, False otherwise
    """
    return hasattr(part, "text") and part.text and part.text.strip()


def has_function_call(part: types.Part) -> bool:
    """Check if a part contains a function call.

    Args:
        part: The part to check

    Returns:
        True if part has a function call, False otherwise
    """
    return hasattr(part, "function_call") and part.function_call


def extract_tool_calls(events: list) -> list[str]:
    """Extract tool call names from events.

    Args:
        events: List of events from callback context

    Returns:
        List of tool call names
    """
    tool_calls = []

    for event in events:
        if not hasattr(event, "content") or not event.content:
            continue

        if not hasattr(event.content, "role") or event.content.role != MODEL_ROLE:
            continue

        if not hasattr(event.content, "parts") or not event.content.parts:
            continue

        for part in event.content.parts:
            if has_function_call(part):
                tool_calls.append(part.function_call.name)

    return tool_calls


def check_for_text_response(events: list) -> bool:
    """Check if events contain any text response.

    Args:
        events: List of events from callback context

    Returns:
        True if text response found, False otherwise
    """
    for event in events:
        if not hasattr(event, "content") or not event.content:
            continue

        # Only check model responses
        if not hasattr(event.content, "role") or event.content.role != MODEL_ROLE:
            continue

        if not hasattr(event.content, "parts") or not event.content.parts:
            continue

        for part in event.content.parts:
            if has_text_content(part):
                return True

    return False


def create_response_content(message: str) -> types.Content:
    """Create a Content object with a text message.

    Args:
        message: The message text

    Returns:
        Content object with the message
    """
    return types.Content(role=MODEL_ROLE, parts=[types.Part(text=message)])


def generate_tool_summary(tool_calls: list[str]) -> str:
    """Generate a summary message for executed tools.

    Args:
        tool_calls: List of tool call names

    Returns:
        Summary message
    """
    # Remove duplicates while preserving order
    unique_tools = list(dict.fromkeys(tool_calls))

    if len(unique_tools) == 1:
        return f"Executed {unique_tools[0]} successfully."

    # Format multiple tools
    if len(unique_tools) == 2:
        return f"Executed the following tools: {unique_tools[0]} and {unique_tools[1]}."

    # Three or more tools
    tools_list = ", ".join(unique_tools[:-1]) + f" and {unique_tools[-1]}"
    return f"Executed the following tools: {tools_list}."


def log_hook_info(plugin_name: str, hook: dict) -> None:
    """Log hook information if present.

    Args:
        plugin_name: Name of the plugin
        hook: Hook dictionary from state
    """
    hook_type = hook.get("type", "unknown")
    logger.info(f"🎣 [{plugin_name}] Hook found in session state: {hook_type}")


class CyodaResponsePlugin(BasePlugin):
    """
    Plugin to ensure quality responses in Cyoda AI Studio.

    Features:
    - Ensures responses are never empty
    - Provides tool execution summaries when agent doesn't generate text
    - Logs hook information for UI integration
    - Validates response quality
    """

    def __init__(
        self,
        name: str = "cyoda_response_plugin",
        provide_tool_summary: bool = True,
        default_message: str = DEFAULT_SUCCESS_MESSAGE,
    ):
        """
        Initialize the Cyoda Response Plugin.

        Args:
            name: Plugin name for identification
            provide_tool_summary: If True, generate tool summaries for empty responses
            default_message: Default message when no tools were executed
        """
        super().__init__(name=name)
        self.provide_tool_summary = provide_tool_summary
        self.default_message = default_message

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        """
        Callback executed after agent completes.

        Ensures the response is not empty and provides meaningful feedback.

        Args:
            agent: The agent that just completed
            callback_context: The callback context

        Returns:
            Content with default/summary message if response is empty, None otherwise
        """
        events = callback_context.session.events

        # Log hook information if present
        hook = callback_context.state.get(HOOK_STATE_KEY)
        if hook:
            log_hook_info(self.name, hook)

        # Check if we have a text response
        if check_for_text_response(events):
            logger.debug(f"✅ [{self.name}] Response validation passed")
            return None

        # No text response - provide meaningful feedback
        return self._generate_fallback_response(events)

    def _generate_fallback_response(self, events: list) -> types.Content:
        """Generate fallback response when no text is present.

        Args:
            events: List of events from callback context

        Returns:
            Content with appropriate fallback message
        """
        if not self.provide_tool_summary:
            logger.info(f"⚠️ [{self.name}] No text response found - providing default message")
            return create_response_content(self.default_message)

        # Try to generate tool summary
        tool_calls = extract_tool_calls(events)

        if tool_calls:
            message = generate_tool_summary(tool_calls)
            logger.info(f"⚠️ [{self.name}] No text response found - providing tool summary: {message}")
            return create_response_content(message)

        # No tools found either - use default message
        logger.info(f"⚠️ [{self.name}] No text response found - providing default message")
        return create_response_content(self.default_message)


class CyodaResponseValidationPlugin(BasePlugin):
    """
    Lightweight plugin that only validates non-empty responses.

    Use this when you want simple validation without tool summaries.
    """

    def __init__(
        self,
        name: str = "cyoda_response_validation_plugin",
        default_message: str = DEFAULT_SUCCESS_MESSAGE,
    ):
        """
        Initialize the validation plugin.

        Args:
            name: Plugin name for identification
            default_message: Message to return when response is empty
        """
        super().__init__(name=name)
        self.default_message = default_message

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        """
        Ensure agent response is not empty.

        Args:
            agent: The agent that just completed
            callback_context: The callback context

        Returns:
            Content with default message if response is empty, None otherwise
        """
        events = callback_context.session.events

        # Check if we have a text response
        if check_for_text_response(events):
            return None

        # No text response - provide default message
        logger.info(f"⚠️ [{self.name}] No text response found - providing default message")
        return create_response_content(self.default_message)
