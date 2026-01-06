"""Prompt Hook Factory - Allows prompts to create hooks directly without tool calls.

This enables prompts to return hooks on-the-fly for dynamic option presentation,
without requiring explicit tool invocations. Perfect for multi-choice questions
and dynamic UI interactions.

Example:
    from application.agents.shared.prompt_hook_factory import create_prompt_hook

    # In a prompt response:
    hook = create_prompt_hook(
        "option_selection",
        conversation_id="conv-123",
        question="What would you like to do?",
        options=[
            {"value": "deploy", "label": "🚀 Deploy"},
            {"value": "check", "label": "✅ Check Status"},
        ]
    )
    return wrap_response_with_hook("Choose an action:", hook)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .hook_factory import get_hook_factory
from .hook_registry import get_hook_registry

logger = logging.getLogger(__name__)


def create_prompt_hook(
    hook_name: str,
    conversation_id: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a hook directly from a prompt without requiring a tool call.

    This allows prompts to return hooks on-the-fly for dynamic option presentation.

    Args:
        hook_name: Name of the hook to create (e.g., "option_selection")
        conversation_id: Conversation ID for context
        **kwargs: Hook-specific parameters (question, options, tab_name, etc.)

    Returns:
        Hook dictionary ready to be wrapped in response

    Raises:
        ValueError: If hook is not registered or parameters are invalid

    Example:
        # Create option selection hook in prompt
        hook = create_prompt_hook(
            "option_selection",
            conversation_id="conv-123",
            question="What would you like to do?",
            options=[
                {"value": "deploy", "label": "🚀 Deploy Environment"},
                {"value": "check", "label": "✅ Check Status"},
            ]
        )

        # Create canvas tab hook in prompt
        hook = create_prompt_hook(
            "open_canvas_tab",
            conversation_id="conv-123",
            tab_name="entities"
        )
    """
    try:
        # Validate hook is registered
        registry = get_hook_registry()
        metadata = registry.get_hook(hook_name)
        if not metadata:
            raise ValueError(f"Hook '{hook_name}' is not registered")

        # Add conversation_id to kwargs
        kwargs["conversation_id"] = conversation_id

        # Use factory to create hook with validation
        factory = get_hook_factory()
        hook = factory.create_hook(hook_name, **kwargs)

        logger.info(f"✅ Created prompt hook: {hook_name} for conversation {conversation_id}")
        return hook

    except Exception as e:
        logger.error(f"❌ Failed to create prompt hook '{hook_name}': {e}")
        raise


def create_option_selection_hook(
    conversation_id: str,
    question: str,
    options: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Create an option selection hook for multi-choice questions in prompts.

    Args:
        conversation_id: Conversation ID
        question: Question to display to user
        options: List of option dicts with 'value' and 'label' keys

    Returns:
        Hook dictionary

    Example:
        hook = create_option_selection_hook(
            conversation_id="conv-123",
            question="What would you like to do?",
            options=[
                {"value": "deploy", "label": "🚀 Deploy"},
                {"value": "check", "label": "✅ Check"},
            ]
        )
    """
    return create_prompt_hook(
        "option_selection",
        conversation_id=conversation_id,
        question=question,
        options=options,
    )


def create_canvas_tab_hook(
    conversation_id: str,
    tab_name: str,
) -> Dict[str, Any]:
    """Create a canvas tab hook in a prompt.

    Args:
        conversation_id: Conversation ID
        tab_name: Tab to open (entities, workflows, requirements, cloud)

    Returns:
        Hook dictionary
    """
    return create_prompt_hook(
        "open_canvas_tab",
        conversation_id=conversation_id,
        tab_name=tab_name,
    )

