"""Prompt Hook Helpers - Utilities for using hooks in prompt responses.

Provides helper functions and patterns for prompts to create and return hooks
without requiring tool calls. Enables dynamic UI interactions directly from
LLM responses.

Key Patterns:
1. Multi-choice questions → option_selection hook
2. Canvas navigation → open_canvas_tab hook
3. Dynamic workflows → combine multiple hooks
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .hook_utils import wrap_response_with_hook
from .prompt_hook_factory import (
    create_option_selection_hook,
    create_canvas_tab_hook,
    create_prompt_hook,
)

logger = logging.getLogger(__name__)


def prompt_ask_user_choice(
    conversation_id: str,
    question: str,
    options: List[Dict[str, str]],
    message: Optional[str] = None,
) -> str:
    """Helper to ask user a multi-choice question with a hook.

    Use this in prompts instead of listing options as text.

    Args:
        conversation_id: Conversation ID
        question: Question to ask
        options: List of options with 'value' and 'label'
        message: Optional message before the hook (defaults to question)

    Returns:
        Message with hook attached

    Example:
        return prompt_ask_user_choice(
            conversation_id=context.conversation_id,
            question="What would you like to do?",
            options=[
                {"value": "deploy", "label": "🚀 Deploy Environment"},
                {"value": "check", "label": "✅ Check Status"},
            ],
            message="I can help you with your environment. Choose an action:"
        )
    """
    try:
        hook = create_option_selection_hook(
            conversation_id=conversation_id,
            question=question,
            options=options,
        )
        display_message = message or question
        return wrap_response_with_hook(display_message, hook)
    except Exception as e:
        logger.error(f"Failed to create choice hook: {e}")
        # Fallback to text-based options
        return f"{question}\n\n" + "\n".join(
            f"- {opt['label']}" for opt in options
        )


def prompt_open_canvas(
    conversation_id: str,
    tab_name: str,
    message: str,
) -> str:
    """Helper to open a canvas tab from a prompt.

    Args:
        conversation_id: Conversation ID
        tab_name: Tab to open (entities, workflows, requirements, cloud)
        message: Message to display with the hook

    Returns:
        Message with canvas tab hook

    Example:
        return prompt_open_canvas(
            conversation_id=context.conversation_id,
            tab_name="entities",
            message="✅ Entity created! Opening Canvas..."
        )
    """
    try:
        hook = create_canvas_tab_hook(
            conversation_id=conversation_id,
            tab_name=tab_name,
        )
        return wrap_response_with_hook(message, hook)
    except Exception as e:
        logger.error(f"Failed to create canvas hook: {e}")
        return message


def prompt_create_hook(
    hook_name: str,
    conversation_id: str,
    message: str,
    **hook_params: Any,
) -> str:
    """Generic helper to create any hook from a prompt.

    Args:
        hook_name: Name of the hook
        conversation_id: Conversation ID
        message: Message to display
        **hook_params: Hook-specific parameters

    Returns:
        Message with hook attached

    Example:
        return prompt_create_hook(
            "option_selection",
            conversation_id=context.conversation_id,
            message="Choose an option:",
            question="What would you like?",
            options=[...]
        )
    """
    try:
        hook = create_prompt_hook(
            hook_name,
            conversation_id=conversation_id,
            **hook_params,
        )
        return wrap_response_with_hook(message, hook)
    except Exception as e:
        logger.error(f"Failed to create hook '{hook_name}': {e}")
        return message

