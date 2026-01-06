"""Canvas and UI element hook utilities.

This module contains hook functions for:
- Proceed button UI
- Canvas integration (deprecated)
- Combined hooks
- Response wrapping
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def create_proceed_button_hook(
    conversation_id: str,
    question: str = "Ready to proceed?",
) -> Dict[str, Any]:
    """
    Create a hook for a simple "Proceed" button confirmation.

    When this hook is returned, the UI should:
    1. Show a "Proceed" button to the user
    2. When clicked, send "Proceed" as a message back to the agent

    Args:
        conversation_id: Conversation technical ID
        question: Question to display to the user

    Returns:
        Hook dictionary with type "option_selection"
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": question,
            "options": [
                {
                    "value": "proceed",
                    "label": "Proceed",
                    "description": "Click to continue"
                }
            ],
            "selection_type": "single"
        }
    }

    logger.info(f"🎣 Created proceed button hook for conversation {conversation_id}")
    return hook


def create_canvas_with_proceed_hook(
    conversation_id: str,
    repository_name: str,
    branch_name: str,
    repository_url: str,
    question: str = "Ready to proceed?",
) -> Dict[str, Any]:
    """
    DEPRECATED: This function is kept for backward compatibility only.

    Use create_proceed_button_hook() instead for a simple proceed button.
    Use create_open_canvas_tab_hook() separately if you need to open canvas.

    The agent should dynamically decide whether to use open_canvas_tab hook
    based on the context and user needs.

    Args:
        conversation_id: Conversation technical ID
        repository_name: Repository name (owner/repo) - IGNORED
        branch_name: Branch name - IGNORED
        repository_url: Full GitHub URL to the branch - IGNORED
        question: Question to display with the proceed button

    Returns:
        Hook dictionary with option_selection (proceed button only)
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": question,
            "options": [
                {
                    "value": "proceed",
                    "label": "Proceed",
                    "description": "Click to continue"
                }
            ],
            "selection_type": "single"
        }
    }

    logger.info(f"🎣 Created proceed button hook for conversation {conversation_id} (canvas_with_proceed deprecated)")
    return hook


def create_combined_hook(
    code_changes_hook: Optional[Dict[str, Any]] = None,
    background_task_hook: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Combine multiple hooks into a single hook response.

    This is useful when an action triggers both code changes and background tasks.

    Args:
        code_changes_hook: Optional code changes hook
        background_task_hook: Optional background task hook

    Returns:
        Combined hook dictionary
    """
    combined = {
        "type": "combined",
        "hooks": []
    }

    if code_changes_hook:
        combined["hooks"].append(code_changes_hook)

    if background_task_hook:
        combined["hooks"].append(background_task_hook)
        # Preserve background_task_ids for backward compatibility
        if "background_task_ids" in background_task_hook:
            combined["background_task_ids"] = background_task_hook["background_task_ids"]

    logger.info(f"🎣 Created combined hook with {len(combined['hooks'])} hooks")
    return combined


def wrap_response_with_hook(
    message: str,
    hook: Dict[str, Any],
) -> str:
    """
    Wrap a response message with a hook for UI integration.

    The hook is stored in tool_context.state["last_tool_hook"] and will be
    included in the SSE done event by StreamingService.

    Args:
        message: Response message to display to user
        hook: Hook dictionary

    Returns:
        JSON string with message and hook
    """
    response = {
        "message": message,
        "hook": hook
    }

    return json.dumps(response, indent=2)
