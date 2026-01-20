"""Conversation-level locking for code generation operations.

Prevents parallel execution of code generation tools (generate_application and
generate_code_with_cli) within the same conversation to avoid conflicts.
"""

from __future__ import annotations

import logging
from typing import Optional

from common.search import CyodaOperator
from common.service.entity_service import SearchConditionRequest

logger = logging.getLogger(__name__)

# Task types that are subject to conversation locking
LOCKED_TASK_TYPES = ["application_build", "code_generation"]


async def check_conversation_lock(
    conversation_id: Optional[str], entity_service
) -> tuple[bool, str]:
    """Check if code generation is already running for this conversation.

    Args:
        conversation_id: Conversation ID to check
        entity_service: Entity service for querying tasks

    Returns:
        Tuple of (is_locked, message):
        - is_locked: True if a task is running (locked), False if safe to proceed
        - message: Description of the lock status or running task
    """
    if not conversation_id:
        # No conversation ID - allow execution (legacy behavior)
        logger.warning("No conversation_id provided - skipping lock check")
        return False, "No conversation lock (no conversation ID)"

    try:
        # Query for running tasks in this conversation
        builder = SearchConditionRequest.builder()
        builder.add_condition("conversation_id", CyodaOperator.EQUALS, conversation_id)
        builder.add_condition("status", CyodaOperator.EQUALS, "running")

        responses = await entity_service.search(
            entity_class="BackgroundTask",
            condition=builder.build(),
            entity_version="1",
        )

        if not responses:
            # No running tasks - safe to proceed
            return False, "No running tasks in conversation"

        # Check if any running task is a code generation task
        for response in responses:
            # Extract task data
            if hasattr(response.data, "model_dump"):
                task_data = response.data.model_dump()
            elif isinstance(response.data, dict):
                task_data = response.data
            else:
                logger.warning(f"Unexpected task data type: {type(response.data)}")
                continue

            task_type = task_data.get("task_type")
            task_name = task_data.get("name", "Unknown task")
            task_id = response.metadata.id if response.metadata else "unknown"

            # Check if this is a locked task type
            if task_type in LOCKED_TASK_TYPES:
                logger.warning(
                    f"🔒 Conversation locked: {task_type} already running "
                    f"(Task ID: {task_id}, Name: {task_name})"
                )
                return True, _format_lock_message(task_type, task_name, task_id)

        # No locked tasks found
        return False, "No code generation tasks running"

    except Exception as e:
        logger.error(f"Failed to check conversation lock: {e}", exc_info=True)
        # On error, allow execution (fail open) but log the error
        return False, f"Lock check failed (allowing execution): {str(e)}"


def _format_lock_message(task_type: str, task_name: str, task_id: str) -> str:
    """Format user-friendly lock message.

    Args:
        task_type: Type of running task
        task_name: Name of running task
        task_id: Technical ID of running task

    Returns:
        Formatted error message
    """
    task_type_display = {
        "application_build": "Application build",
        "code_generation": "Code generation",
    }.get(task_type, task_type)

    return f"""❌ {task_type_display} already running for this conversation

Task: {task_name}
Task ID: {task_id}

Only one code generation task can run at a time per conversation.
Please wait for the current task to complete before starting a new one.

You can check task status using:
  check_task_status(task_id='{task_id}')
"""


__all__ = ["check_conversation_lock"]
