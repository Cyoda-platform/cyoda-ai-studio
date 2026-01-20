"""Tool for checking background task status by task ID.

Allows users to check the status of code generation, builds, and other background tasks.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def check_task_status(
    task_id: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Check the status of a background task (build, code generation, deployment, etc.).

    This tool allows you to check the current status of any background task by its ID.
    Use this when the user asks about a task that's running or has completed.

    **When to use:**
    - User asks "what's the status of task xyz?"
    - User provides a task ID they received earlier
    - User wants to know if a build/generation is complete
    - User wants to check if a task failed and see error details

    Args:
        task_id: The technical ID of the background task (UUID format)
        tool_context: Execution context (auto-injected)

    Returns:
        Formatted status message with task details

    Examples:
        >>> await check_task_status("c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe")
        '''
        📋 Task Status: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

        Status: completed ✅
        Progress: 100%
        Name: Build python application: feature-branch

        Started: 2024-01-19 15:08:23
        Completed: 2024-01-19 15:12:45
        Duration: 4 minutes 22 seconds

        Files changed: 15
        Branch: feature-branch
        '''

    Error Cases:
        - Task not found
        - Invalid task ID format
        - Permission denied (task belongs to different user)
    """
    from services.services import get_task_service

    try:
        # Validate task ID format (basic check)
        if not task_id or len(task_id) < 10:
            return f"ERROR: Invalid task ID format: {task_id}"

        # Get task from service
        task_service = get_task_service()
        task = await task_service.get_task(task_id)

        if not task:
            return f"ERROR: Task not found: {task_id}\n\nPossible reasons:\n- Task ID is incorrect\n- Task was deleted\n- Task belongs to a different user"

        # Format status with emoji
        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫",
        }
        emoji = status_emoji.get(task.status, "❓")

        # Build status message
        message = f"📋 Task Status: {task_id}\n\n"
        message += f"Status: {task.status} {emoji}\n"
        message += f"Progress: {task.progress}%\n"

        if task.name:
            message += f"Name: {task.name}\n"

        if task.description:
            message += f"Description: {task.description}\n"

        message += "\n"

        # Time information
        if task.started_at:
            message += f"Started: {task.started_at}\n"

        if task.completed_at:
            message += f"Completed: {task.completed_at}\n"

        if task.started_at and task.completed_at:
            # Calculate duration
            from datetime import datetime

            try:
                start = datetime.fromisoformat(task.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(task.completed_at.replace("Z", "+00:00"))
                duration = end - start
                minutes = int(duration.total_seconds() / 60)
                seconds = int(duration.total_seconds() % 60)

                if minutes > 0:
                    message += f"Duration: {minutes} minute{'s' if minutes != 1 else ''} {seconds} second{'s' if seconds != 1 else ''}\n"
                else:
                    message += (
                        f"Duration: {seconds} second{'s' if seconds != 1 else ''}\n"
                    )
            except Exception:
                pass

        # Task-specific information
        message += "\n"

        if task.branch_name:
            message += f"Branch: {task.branch_name}\n"

        if task.language:
            message += f"Language: {task.language}\n"

        if task.repository_path:
            message += f"Repository: {task.repository_path}\n"

        # Progress messages (last 3)
        if task.progress_messages and len(task.progress_messages) > 0:
            message += "\n📝 Recent Updates:\n"
            recent_messages = task.progress_messages[-3:]
            for msg in recent_messages:
                if isinstance(msg, dict):
                    msg_text = msg.get("message", "")
                    msg_time = msg.get("last_modified_at", "")
                    if msg_text:
                        message += f"  • {msg_text}"
                        if msg_time:
                            message += f" ({msg_time})"
                        message += "\n"

        # Metadata (files changed, errors, etc.)
        if task.metadata:
            metadata = task.metadata

            # Files changed
            changed_files = metadata.get("changed_files", [])
            if changed_files:
                file_count = len(changed_files)
                message += f"\n📁 Files changed: {file_count}\n"

            # Error information
            if task.status == "failed":
                message += "\n"
                error_type = metadata.get("error_type", "unknown")
                error_desc = metadata.get("error_description", "Unknown error")
                is_retryable = metadata.get("is_retryable", False)

                message += f"❌ Error Details:\n"
                message += f"  Type: {error_type}\n"
                message += f"  Description: {error_desc}\n"
                message += f"  Retryable: {'Yes ✅' if is_retryable else 'No ❌'}\n"

                if task.error:
                    message += f"\n  Full error:\n"
                    # Show first 500 chars of error
                    error_preview = (
                        task.error[:500] + "..."
                        if len(task.error) > 500
                        else task.error
                    )
                    message += f"  {error_preview}\n"

        # Result information
        if task.result:
            message += f"\n✅ Result: {task.result}\n"

        # Next steps based on status
        message += "\n"
        if task.status == "running":
            message += "⏳ Task is still running. Check back later for updates.\n"
        elif task.status == "completed":
            message += "✅ Task completed successfully!\n"
            if task.branch_name and task.repository_path:
                message += f"\nNext steps:\n"
                message += f"  • Review changes in branch: {task.branch_name}\n"
                message += f"  • Check repository: {task.repository_path}\n"
        elif task.status == "failed":
            is_retryable = (
                task.metadata.get("is_retryable", False) if task.metadata else False
            )
            message += "❌ Task failed.\n"
            if is_retryable:
                message += f"\nYou can retry this task using:\n"
                message += f"  retry_failed_generation(task_id='{task_id}')\n"
            else:
                message += "\nThis error is not retryable. Please review the error and fix the underlying issue.\n"

        return message

    except Exception as e:
        logger.error(f"Failed to check task status for {task_id}: {e}", exc_info=True)
        return f"ERROR: Failed to retrieve task status: {str(e)}"


__all__ = ["check_task_status"]
