"""Tool for displaying interactive setup options to the user."""

from __future__ import annotations

import json
import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.hooks import creates_hook
from application.agents.shared.tool_context_helpers import get_conversation_id

logger = logging.getLogger(__name__)


@creates_hook("option_selection")
def show_setup_options(
    question: str,
    options: list[dict[str, str]],
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Display interactive setup menu options to the user.

    This tool allows the Setup Agent to present menu options as clickable UI elements
    instead of plain text. Use this for the initial setup menu (A-E options) or any
    other scenario where the user needs to choose from multiple options.

    Args:
        question: Question to ask the user (displayed as title)
        options: List of option dictionaries with 'value', 'label', and optional 'description'
                Example: [
                    {
                        "value": "check_env",
                        "label": "🌐 Check Environment Status",
                        "description": "Verify if your Cyoda cloud is ready"
                    },
                    {
                        "value": "local_setup",
                        "label": "🚀 Local Setup Guide",
                        "description": "Step-by-step commands to run your app"
                    }
                ]
        tool_context: The ADK tool context (auto-injected)

    Returns:
        JSON string confirming options are displayed

    Example usage in prompt:
        "To show the setup menu, call show_setup_options with:
        - question: 'How would you like to proceed?'
        - options: [your menu options]"
    """
    try:
        if tool_context is None:
            return "ERROR: Tool context not available. Cannot display options."

        conversation_id = get_conversation_id(tool_context)
        if not conversation_id:
            return "ERROR: No conversation_id in context. Cannot display options."

        # Validate options
        if not options or not isinstance(options, list):
            return "ERROR: Options must be a non-empty list."

        for opt in options:
            if not isinstance(opt, dict) or "value" not in opt or "label" not in opt:
                return "ERROR: Each option must be a dictionary with 'value' and 'label' keys."

        # Create option selection hook
        from application.agents.shared.hooks import (
            create_option_selection_hook,
            wrap_response_with_hook,
        )

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
        error_msg = f"Error displaying setup options: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})
