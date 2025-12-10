# Prompt-Level Hooks Guide

## Overview

Prompts can now **return hooks directly without requiring tool calls**. This enables dynamic UI interactions and multi-choice options to be created on-the-fly from LLM responses.

## Key Benefit

Instead of asking users to type responses to text-based options, prompts can return clickable buttons directly.

## Quick Start

### Before (Text-Based Options)
```python
def my_prompt_response(context):
    return """What would you like to do?
1. Deploy environment
2. Check status
3. Issue credentials

Please reply with your choice (1, 2, or 3)"""
```

### After (Hook-Based Options)
```python
from application.agents.shared.prompt_hook_helpers import prompt_ask_user_choice

def my_prompt_response(context):
    return prompt_ask_user_choice(
        conversation_id=context["conversation_id"],
        question="What would you like to do?",
        options=[
            {"value": "deploy", "label": "🚀 Deploy Environment"},
            {"value": "check", "label": "✅ Check Status"},
            {"value": "credentials", "label": "🔐 Issue Credentials"},
        ],
        message="I can help you manage your environment."
    )
```

## Available Helpers

### 1. `prompt_ask_user_choice()` - Multi-Choice Questions

Create interactive option selection without tool calls.

```python
from application.agents.shared.prompt_hook_helpers import prompt_ask_user_choice

response = prompt_ask_user_choice(
    conversation_id=context["conversation_id"],
    question="What would you like to do?",
    options=[
        {"value": "deploy", "label": "🚀 Deploy"},
        {"value": "check", "label": "✅ Check"},
    ],
    message="Choose an action:"  # Optional
)
```

### 2. `prompt_open_canvas()` - Canvas Navigation

Open canvas tabs directly from prompts.

```python
from application.agents.shared.prompt_hook_helpers import prompt_open_canvas

response = prompt_open_canvas(
    conversation_id=context["conversation_id"],
    tab_name="entities",  # or "workflows", "requirements", "cloud"
    message="✅ Entity created! Opening Canvas..."
)
```

### 3. `prompt_create_hook()` - Generic Hook Creation

Create any registered hook from a prompt.

```python
from application.agents.shared.prompt_hook_helpers import prompt_create_hook

response = prompt_create_hook(
    "option_selection",
    conversation_id=context["conversation_id"],
    message="Choose your language:",
    question="Which language?",
    options=[
        {"value": "python", "label": "🐍 Python"},
        {"value": "java", "label": "☕ Java"},
    ]
)
```

## Use Cases

### 1. Conditional Options Based on Context
```python
def my_prompt(context):
    if context.get("has_environment"):
        return prompt_ask_user_choice(
            conversation_id=context["conversation_id"],
            question="What's next?",
            options=[
                {"value": "deploy_app", "label": "Deploy App"},
                {"value": "view_logs", "label": "View Logs"},
            ]
        )
    else:
        return prompt_ask_user_choice(
            conversation_id=context["conversation_id"],
            question="Create environment?",
            options=[
                {"value": "deploy", "label": "Deploy"},
            ]
        )
```

### 2. Multi-Step Workflows
```python
def my_prompt(context):
    # Step 1: Ask what to create
    return prompt_ask_user_choice(
        conversation_id=context["conversation_id"],
        question="What would you like to create?",
        options=[
            {"value": "entity", "label": "Entity"},
            {"value": "workflow", "label": "Workflow"},
        ],
        message="Let's build something new!"
    )
```

### 3. Navigation After Actions
```python
def my_prompt(context):
    # After describing what was created
    return prompt_open_canvas(
        conversation_id=context["conversation_id"],
        tab_name="entities",
        message="✅ Customer entity created! Opening Canvas to view it..."
    )
```

## Hook Structure

Hooks created by prompts follow the same structure as tool-created hooks:

```python
{
    "name": "option_selection",
    "type": "option_selection",
    "parameters": {
        "conversation_id": "conv-123",
        "question": "What would you like to do?",
        "options": [
            {"value": "deploy", "label": "🚀 Deploy"},
            {"value": "check", "label": "✅ Check"},
        ]
    }
}
```

## Registered Hooks

- `option_selection` - Multi-choice questions
- `open_canvas_tab` - Canvas navigation
- `code_changes` - Code refresh
- `background_task` - Long-running tasks
- `cloud_window` - Cloud panel
- `issue_technical_user` - M2M credentials

## Error Handling

Helpers gracefully fall back to text if hook creation fails:

```python
response = prompt_ask_user_choice(...)
# If hook creation fails, returns text-based options instead
```

## Testing

See `tests/test_prompt_hooks.py` for comprehensive examples.

## Key Principles

✅ **Dynamic** - Create different hooks based on context
✅ **No Tool Calls** - Hooks created directly in prompts
✅ **Validated** - All hooks validated at creation time
✅ **Reusable** - Use same helpers across all prompts
✅ **Graceful Fallback** - Text options if hook creation fails

