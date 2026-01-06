"""Helpers for creating code generation UI hooks."""

from __future__ import annotations

import logging
from typing import Optional

from application.agents.shared.hooks.hook_utils import (
    create_background_task_hook,
    wrap_response_with_hook,
)

logger = logging.getLogger(__name__)


def _create_codegen_hook(
    task_id: str,
    user_request: str,
    language: str,
    branch_name: str,
    process_pid: int,
    conversation_id: Optional[str],
) -> dict:
    """Create background task hook for code generation.

    Args:
        task_id: Background task ID
        user_request: User's code generation request
        language: Programming language
        branch_name: Branch name
        process_pid: Process PID
        conversation_id: Conversation ID

    Returns:
        Hook dictionary
    """
    hook = create_background_task_hook(
        task_id=task_id,
        task_type="code_generation",
        task_name=f"Generate code: {user_request[:50]}...",
        task_description=f"Generating code with CLI: {user_request[:200]}...",
        conversation_id=conversation_id,
        metadata={
            "branch_name": branch_name,
            "language": language,
            "process_pid": process_pid,
        },
    )

    return hook


def _format_codegen_response(
    task_id: str,
    branch_name: str,
    user_request: str,
    hook: dict,
) -> str:
    """Format code generation started response message.

    Args:
        task_id: Task ID
        branch_name: Branch name
        user_request: User request
        hook: Hook dictionary

    Returns:
        Formatted response with hook
    """
    message = f"""🤖 Code generation started with CLI!

📋 **Task ID:** {task_id}
🌿 **Branch:** {branch_name}
📝 **Request:** {user_request[:100]}{"..." if len(user_request) > 100 else ""}

⏳ Code generation is running in the background. I'll update you when it completes.
You can continue chatting while the code is being generated.

Click 'View Tasks' to monitor progress."""

    return wrap_response_with_hook(message, hook)


def _format_codegen_response_without_task(
    branch_name: str,
    user_request: str,
) -> str:
    """Format code generation response when task creation failed.

    Args:
        branch_name: Branch name
        user_request: User request

    Returns:
        Formatted response message
    """
    return f"""🤖 Code generation started with CLI!

🌿 **Branch:** {branch_name}
📝 **Request:** {user_request[:100]}{"..." if len(user_request) > 100 else ""}

⏳ Code generation is running in the background. I'll update you when it completes."""
