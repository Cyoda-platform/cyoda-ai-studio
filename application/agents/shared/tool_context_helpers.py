"""Helper utilities for working with ToolContext.

This module provides helper functions for extracting common values
from ToolContext across different execution environments (coordinator vs standalone ADK).
"""

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# Check if ADK test mode is enabled (allows fallback to session.id)
_ADK_TEST_MODE = os.getenv("ADK_TEST_MODE", "").lower() in ("true", "1", "yes")


def get_conversation_id(tool_context: Optional[ToolContext]) -> str:
    """Get conversation_id from tool_context with optional fallback to session.id.

    When running via the coordinator, conversation_id is set in tool_context.state.
    When running via standalone ADK web in test mode (ADK_TEST_MODE=true),
    fallback to session.id is allowed. In production, missing conversation_id
    returns empty string to fail properly.

    Args:
        tool_context: Tool execution context (optional)

    Returns:
        Conversation ID (from state) or session ID (test mode fallback) or empty string
    """
    if not tool_context:
        logger.warning("get_conversation_id called without tool_context")
        return ""

    # Try to get from state first (coordinator mode)
    conversation_id = tool_context.state.get("conversation_id", "")

    if conversation_id:
        return conversation_id

    # Fallback to session.id only in ADK test mode (for standalone ADK web testing)
    if _ADK_TEST_MODE:
        try:
            if hasattr(tool_context, "session") and tool_context.session:
                session_id = tool_context.session.id
                logger.debug(
                    f"🧪 Test mode: Using session.id as conversation_id: {session_id}"
                )
                return session_id
        except Exception as e:
            logger.warning(f"Failed to get session.id from tool_context: {e}")

    # In production mode, return empty string to fail properly
    return ""


def get_session_id(tool_context: Optional[ToolContext]) -> str:
    """Get session ID from tool_context.

    Args:
        tool_context: Tool execution context (optional)

    Returns:
        Session ID or empty string
    """
    if not tool_context:
        logger.warning("get_session_id called without tool_context")
        return ""

    try:
        if hasattr(tool_context, "session") and tool_context.session:
            return tool_context.session.id
    except Exception as e:
        logger.warning(f"Failed to get session.id from tool_context: {e}")

    return ""


def get_user_id(tool_context: Optional[ToolContext]) -> str:
    """Get user ID from tool_context.

    Args:
        tool_context: Tool execution context (optional)

    Returns:
        User ID or empty string
    """
    if not tool_context:
        logger.warning("get_user_id called without tool_context")
        return ""

    # Try state first
    user_id = tool_context.state.get("user_id", "")
    if user_id:
        return user_id

    # Try session
    try:
        if hasattr(tool_context, "session") and tool_context.session:
            return tool_context.session.user_id
    except Exception as e:
        logger.warning(f"Failed to get user_id from tool_context: {e}")

    return ""
