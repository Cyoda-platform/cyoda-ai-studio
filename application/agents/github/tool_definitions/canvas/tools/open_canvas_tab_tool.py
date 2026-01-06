"""Tool for opening canvas tabs in the UI.

This module provides functionality to open specific canvas tabs in the UI.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import STOP_ON_ERROR
from application.agents.shared.hooks import creates_hook

logger = logging.getLogger(__name__)


@creates_hook("open_canvas_tab")
async def open_canvas_tab(
    tab_name: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Open a specific canvas tab in the UI.

    This tool creates a hook that instructs the UI to open a specific canvas tab.
    The LLM can use this to guide users to view entities, workflows, requirements, or cloud settings.

    Args:
        tab_name: Name of the canvas tab to open. Valid values:
            - "entities" - Opens Canvas Entities tab
            - "workflows" - Opens Canvas Workflows tab
            - "requirements" - Opens Canvas Requirements tab
            - "cloud" - Opens Cloud/Environments tab
        tool_context: The ADK tool context

    Returns:
        Success message with canvas_tab hook

    Raises:
        ValueError: If tab_name is not one of the valid options

    Examples:
        >>> await open_canvas_tab("entities", tool_context)
        "✅ Opening Canvas Entities tab..."

        >>> await open_canvas_tab("workflows", tool_context)
        "✅ Opening Canvas Workflows tab..."

        >>> await open_canvas_tab("cloud", tool_context)
        "✅ Opening Cloud tab..."
    """
    try:
        from application.agents.shared.hooks import create_open_canvas_tab_hook, wrap_response_with_hook

        if not tool_context:
            return f"ERROR: Tool context not available.{STOP_ON_ERROR}"

        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}"

        # Validate tab_name
        valid_tabs = ["entities", "workflows", "requirements", "cloud"]
        if tab_name not in valid_tabs:
            return f"ERROR: Invalid tab_name '{tab_name}'. Must be one of: {', '.join(valid_tabs)}.{STOP_ON_ERROR}"

        # Create the hook
        hook = create_open_canvas_tab_hook(
            conversation_id=conversation_id,
            tab_name=tab_name,
        )

        # Store hook in context for SSE streaming
        tool_context.state["last_tool_hook"] = hook

        # Create appropriate message based on tab
        tab_messages = {
            "entities": "✅ Opening Canvas Entities tab to view and manage your entities.",
            "workflows": "✅ Opening Canvas Workflows tab to view and manage your workflows.",
            "requirements": "✅ Opening Canvas Requirements tab to view and manage your requirements.",
            "cloud": "✅ Opening Cloud tab to view your environment details.",
        }

        message = tab_messages.get(tab_name, f"✅ Opening Canvas {tab_name} tab...")

        logger.info(f"🎨 Opening canvas tab: {tab_name} for conversation {conversation_id}")
        return wrap_response_with_hook(message, hook)

    except Exception as e:
        logger.error(f"Error opening canvas tab: {e}", exc_info=True)
        return f"ERROR: Failed to open canvas tab: {str(e)}"
