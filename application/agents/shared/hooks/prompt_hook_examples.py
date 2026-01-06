"""Examples of using hooks directly in prompts without tool calls.

These examples show how to return hooks on-the-fly from prompt responses
for dynamic option presentation and UI interactions.
"""

from __future__ import annotations

from typing import Any

from .prompt_hook_helpers import (
    prompt_ask_user_choice,
    prompt_open_canvas,
    prompt_create_hook,
)


def example_prompt_with_options(context: Any) -> str:
    """Example: Prompt returns multi-choice options without tool call.

    Instead of asking "Would you like to deploy or check status?",
    return a hook that renders as clickable buttons.
    """
    conversation_id = context.get("conversation_id", "unknown")

    return prompt_ask_user_choice(
        conversation_id=conversation_id,
        question="What would you like to do with your environment?",
        options=[
            {
                "value": "deploy",
                "label": "🚀 Deploy New Environment",
                "description": "Create a new Cyoda environment"
            },
            {
                "value": "check",
                "label": "✅ Check Existing Environment",
                "description": "Check if you have an existing environment"
            },
            {
                "value": "credentials",
                "label": "🔐 Issue Credentials",
                "description": "Get M2M credentials for API access"
            },
        ],
        message="I can help you manage your Cyoda environment. Choose an action:"
    )


def example_prompt_with_canvas_navigation(context: Any) -> str:
    """Example: Prompt opens canvas tab without tool call.

    After describing what was created, directly open the canvas
    for the user to view it.
    """
    conversation_id = context.get("conversation_id", "unknown")

    return prompt_open_canvas(
        conversation_id=conversation_id,
        tab_name="entities",
        message="""✅ Customer entity created successfully!

**Fields:**
- id: UUID (primary key)
- name: String (required)
- email: String (unique)
- created_at: Timestamp

Opening Canvas to view your entity..."""
    )


def example_prompt_with_dynamic_workflow(context: Any) -> str:
    """Example: Prompt with conditional hook creation.

    Create different hooks based on context/state.
    """
    conversation_id = context.get("conversation_id", "unknown")
    user_has_environment = context.get("has_environment", False)

    if user_has_environment:
        # User has environment - offer actions
        return prompt_ask_user_choice(
            conversation_id=conversation_id,
            question="Your environment is ready. What's next?",
            options=[
                {"value": "deploy_app", "label": "📦 Deploy Application"},
                {"value": "view_logs", "label": "📋 View Logs"},
                {"value": "scale", "label": "⚙️ Scale Resources"},
            ],
            message="Your Cyoda environment is deployed and ready to use."
        )
    else:
        # No environment - offer to create one
        return prompt_ask_user_choice(
            conversation_id=conversation_id,
            question="You don't have a Cyoda environment yet. Would you like to create one?",
            options=[
                {"value": "deploy", "label": "🚀 Deploy Environment"},
                {"value": "learn_more", "label": "📚 Learn More"},
            ],
            message="Let's get you set up with a Cyoda environment."
        )


def example_prompt_with_generic_hook(context: Any) -> str:
    """Example: Using generic hook creation for custom scenarios."""
    conversation_id = context.get("conversation_id", "unknown")

    return prompt_create_hook(
        "option_selection",
        conversation_id=conversation_id,
        message="Choose your programming language:",
        question="Which language would you like to use?",
        options=[
            {"value": "python", "label": "🐍 Python"},
            {"value": "java", "label": "☕ Java"},
            {"value": "typescript", "label": "📘 TypeScript"},
        ]
    )


# ============================================================================
# PATTERN: How to use in actual prompts
# ============================================================================

PROMPT_PATTERN = """
# Example: Using Hooks in Prompts

Instead of this (OLD - text-based options):
```
User: "What should I do?"
Agent: "You have two options:
1. Deploy environment
2. Check status
Please reply with your choice (1 or 2)"
```

Do this (NEW - hook-based options):
```python
# In your prompt response function:
from .prompt_hook_helpers import prompt_ask_user_choice

def my_prompt_response(context):
    return prompt_ask_user_choice(
        conversation_id=context["conversation_id"],
        question="What would you like to do?",
        options=[
            {"value": "deploy", "label": "🚀 Deploy"},
            {"value": "check", "label": "✅ Check"},
        ],
        message="I can help you manage your environment."
    )
```

Benefits:
✅ User sees clickable buttons instead of text options
✅ No tool call required - hook created directly in prompt
✅ Cleaner UX - no need to type responses
✅ Dynamic - create different options based on context
✅ Reusable - use helper functions across prompts
"""

