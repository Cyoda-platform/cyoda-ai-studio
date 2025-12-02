"""
Cyoda Response Plugin for ensuring quality agent responses.

This plugin provides:
1. Non-empty response validation
2. Hook extraction and propagation
3. Response enhancement with tool summaries

Based on ADK BasePlugin pattern:
https://google.github.io/adk-docs/callbacks/
"""

import logging
from typing import Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

logger = logging.getLogger(__name__)


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
        default_message: str = "Task completed successfully.",
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
                            # Check for non-empty text (excluding whitespace)
                            if hasattr(part, "text") and part.text and part.text.strip():
                                has_text_response = True
                            # Track tool calls
                            if hasattr(part, "function_call") and part.function_call:
                                tool_calls.append(part.function_call.name)

        # Log hook information if present
        hook = callback_context.state.get("last_tool_hook")
        if hook:
            logger.info(
                f"🎣 [{self.name}] Hook found in session state: {hook.get('type', 'unknown')}"
            )

        # If no text response found, provide a meaningful message
        if not has_text_response:
            if self.provide_tool_summary and tool_calls:
                # Generate summary of tools executed
                unique_tools = list(
                    dict.fromkeys(tool_calls)
                )  # Preserve order, remove duplicates
                if len(unique_tools) == 1:
                    message = f"Executed {unique_tools[0]} successfully."
                else:
                    tools_list = (
                        ", ".join(unique_tools[:-1]) + f" and {unique_tools[-1]}"
                    )
                    message = f"Executed the following tools: {tools_list}."

                logger.info(
                    f"⚠️ [{self.name}] No text response found - providing tool summary: {message}"
                )
                return types.Content(role="model", parts=[types.Part(text=message)])
            else:
                # No tools or tool summary disabled - use default message
                logger.info(
                    f"⚠️ [{self.name}] No text response found - providing default message"
                )
                return types.Content(
                    role="model", parts=[types.Part(text=self.default_message)]
                )

        # Response is valid, allow it to proceed
        logger.debug(f"✅ [{self.name}] Response validation passed")
        return None


class CyodaResponseValidationPlugin(BasePlugin):
    """
    Lightweight plugin that only validates non-empty responses.

    Use this when you want simple validation without tool summaries.
    """

    def __init__(
        self,
        name: str = "cyoda_response_validation_plugin",
        default_message: str = "Task completed successfully.",
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
                            if (
                                hasattr(part, "text")
                                and part.text
                                and part.text.strip()
                            ):
                                has_text_response = True
                                break
            if has_text_response:
                break

        # If no text response found, provide a default message
        if not has_text_response:
            logger.info(
                f"⚠️ [{self.name}] No text response found - providing default message"
            )
            return types.Content(
                role="model", parts=[types.Part(text=self.default_message)]
            )

        # Response is valid, allow it to proceed
        return None

