"""Event processing utilities for streaming."""

import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_tool_hook_from_response(
    tool_response: Dict[str, Any],
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Extract message and hook from tool response JSON.

    Args:
        tool_response: Tool response dictionary

    Returns:
        Tuple of (tool_message, tool_hook)
    """
    tool_message = None
    tool_hook = None

    if not tool_response or "result" not in tool_response:
        return tool_message, tool_hook

    result_str = tool_response.get("result", "")
    if not isinstance(result_str, str):
        return tool_message, tool_hook

    try:
        result_json = json.loads(result_str)
        if isinstance(result_json, dict):
            tool_message = result_json.get("message")
            tool_hook = result_json.get("hook")
    except (json.JSONDecodeError, ValueError):
        pass

    return tool_message, tool_hook


def extract_ui_functions_from_session(
    session: Any,
    current_ui_functions: list,
) -> list:
    """Extract new UI functions from session state.

    Args:
        session: Session object
        current_ui_functions: List to accumulate UI functions

    Returns:
        Updated list of UI functions
    """
    if not session or "ui_functions" not in session.state:
        return current_ui_functions

    session_ui_functions = session.state.get("ui_functions", [])
    logger.info(f"📋 Found {len(session_ui_functions)} ui_functions in session state")

    for ui_func in session_ui_functions:
        if ui_func not in current_ui_functions:
            current_ui_functions.append(ui_func)
            logger.info(
                f"📋 Collected ui_function from stream: {ui_func.get('function', 'unknown')}"
            )

    return current_ui_functions


def extract_repository_info(
    session_state: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Extract repository info from session state.

    Args:
        session_state: Session state dictionary

    Returns:
        Repository info dict or None
    """
    if not all(
        [
            session_state.get("repository_name"),
            session_state.get("repository_owner"),
            session_state.get("branch_name"),
        ]
    ):
        return None

    return {
        "repository_name": session_state.get("repository_name"),
        "repository_owner": session_state.get("repository_owner"),
        "repository_branch": session_state.get("branch_name"),
        "repository_url": session_state.get("repository_url"),
        "installation_id": session_state.get("installation_id"),
    }
