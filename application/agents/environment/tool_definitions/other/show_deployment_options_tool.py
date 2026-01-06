"""Tool for displaying interactive deployment options."""

from __future__ import annotations

import json
import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.hooks import creates_hook
from application.agents.shared.tool_context_helpers import get_conversation_id

logger = logging.getLogger(__name__)


@creates_hook("option_selection")
def show_deployment_options(
        question: str,
        options: list[dict[str, str]],
        tool_context: Optional[ToolContext] = None,
) -> str:
    """Display interactive deployment options to the user.

    This tool allows the LLM to dynamically present options based on the situation.
    The user's selection will be sent back as a message that the agent can parse.

    Args:
        question: Question to ask the user (displayed as title)
        options: List of option dictionaries with 'value', 'label', and optional 'description' (REQUIRED)
        tool_context: The ADK tool context (optional)

    Returns:
        JSON string confirming options are displayed

    Raises:
        ValueError: If validation fails for question, options, or tool_context
    """
    try:
        if tool_context is None:
            raise ValueError("Tool context is required. Cannot display options without context.")

        conversation_id = get_conversation_id(tool_context)
        if not conversation_id:
            raise ValueError("No conversation_id in context. Cannot display options.")

        # Validate question
        if not question or not isinstance(question, str) or not question.strip():
            raise ValueError("The 'question' parameter is required and must be a non-empty string.")

        # Validate options
        if not options or not isinstance(options, list):
            raise ValueError("The 'options' parameter is required and must be a non-empty list.")

        for i, opt in enumerate(options):
            if not isinstance(opt, dict):
                raise ValueError(f"Option at index {i} is not a dictionary")
            if "value" not in opt:
                raise ValueError(f"Option at index {i} is missing required 'value' field")
            if "label" not in opt:
                raise ValueError(f"Option at index {i} is missing required 'label' field")

        # Create option selection hook
        from application.agents.shared.hooks import create_option_selection_hook, wrap_response_with_hook

        hook = create_option_selection_hook(
            conversation_id=conversation_id,
            question=question,
            options=options,
        )

        # Store hook in context
        tool_context.state["last_tool_hook"] = hook

        message = f"{question}\n\nPlease select your choice from the options above."
        return wrap_response_with_hook(message, hook)

    except Exception as e:
        error_msg = f"Error displaying deployment options: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})
