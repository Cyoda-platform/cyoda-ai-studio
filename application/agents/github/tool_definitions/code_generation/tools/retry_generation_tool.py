"""Tool for retrying failed code generation tasks.

Allows users to retry failed CLI processes (builds, code generation)
with automatic error classification and retry recommendations.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.code_generation.helpers import (
    CliErrorType,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)


async def retry_failed_generation(
    task_id: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Retry a failed code generation or application build task.

    This tool allows you to retry a failed CLI process (application build or code generation)
    that previously failed. The system automatically:
    - Checks if the error is retryable
    - Verifies circuit breaker status
    - Extracts original parameters from the failed task
    - Restarts the process with the same configuration

    **When to use this tool:**
    - After a transient error (rate limits, network issues, timeouts)
    - When the error message indicates the failure may be retryable
    - After fixing underlying issues (API keys, network connectivity)

    **When NOT to use this tool:**
    - For permanent errors (syntax errors, invalid configuration)
    - When the error description says "unlikely to succeed on retry"
    - Before addressing the root cause of the failure

    Args:
        task_id: Technical ID of the failed BackgroundTask to retry
        tool_context: Execution context (auto-injected)

    Returns:
        Success message with new task ID or error explaining why retry is not recommended

    Example:
        >>> await retry_failed_generation("abc123-task-id")
        "✅ Retrying task abc123-task-id. New task ID: xyz789-task-id"

    Errors:
        - Task not found
        - Task not in failed state
        - Error is not retryable (permanent error)
        - Circuit breaker is open (too many recent failures)
        - Missing original parameters in task metadata
    """
    from services.services import get_task_service

    try:
        # Step 1: Get task details
        task_service = get_task_service()
        task = await task_service.get_task(task_id)

        if not task:
            return f"ERROR: Task {task_id} not found"

        # Step 2: Validate task can be retried
        if task.status != "failed":
            return (
                f"ERROR: Task {task_id} is not in failed state (current status: {task.status}). "
                f"Only failed tasks can be retried."
            )

        # Step 3: Check if error is retryable
        metadata = task.metadata or {}
        error_type_str = metadata.get("error_type", "unknown")
        is_retryable = metadata.get("is_retryable", False)
        error_description = metadata.get("error_description", "Unknown error")

        if not is_retryable:
            # Provide specific guidance based on error type
            guidance = "Please review the error details and fix the underlying issue before creating a new task."

            # Syntax/compilation errors
            if any(
                x in error_description.lower()
                for x in ["syntax", "compilation", "invalid syntax", "generated code"]
            ):
                guidance = (
                    "The generated code has syntax or compilation errors.\n\n"
                    "Recommended actions:\n"
                    "  1. Review and clarify your requirements\n"
                    "  2. Simplify the request if it's too complex\n"
                    "  3. Check if the requirements contain conflicting instructions"
                )
            # Authentication/config errors
            elif any(
                x in error_description.lower()
                for x in ["authentication", "api key", "permission", "configuration"]
            ):
                guidance = (
                    "Authentication or configuration issue.\n\n"
                    "Recommended actions:\n"
                    "  1. Verify API keys are valid and not expired\n"
                    "  2. Check configuration settings\n"
                    "  3. Ensure you have necessary permissions"
                )

            return (
                f"❌ Cannot retry task {task_id}:\n\n"
                f"Error type: {error_type_str}\n"
                f"Description: {error_description}\n\n"
                f"This error is classified as PERMANENT and is unlikely to succeed on retry.\n\n"
                f"{guidance}"
            )

        # Step 4: Check circuit breaker
        circuit_breaker = get_circuit_breaker()
        can_execute, reason = circuit_breaker.can_execute()
        if not can_execute:
            return (
                f"⚠️ Cannot retry task {task_id} at this time:\n\n"
                f"{reason}\n\n"
                f"The circuit breaker is currently OPEN due to too many recent failures. "
                f"This is a protective mechanism to prevent cascading failures. "
                f"Please wait for the circuit breaker to reset before retrying."
            )

        # Step 5: Extract task type and original parameters
        task_type = task.task_type
        language = task.language
        repository_path = task.repository_path
        branch_name = task.branch_name
        user_request = task.user_request

        if not all([task_type, repository_path, branch_name]):
            return (
                f"ERROR: Cannot retry task {task_id} - missing required parameters in task metadata:\n"
                f"- task_type: {task_type}\n"
                f"- repository_path: {repository_path}\n"
                f"- branch_name: {branch_name}\n"
                f"- user_request: {user_request}"
            )

        # Step 6: Log retry attempt
        logger.info(
            f"🔄 Retrying task {task_id}:\n"
            f"  Type: {task_type}\n"
            f"  Error: {error_description}\n"
            f"  Language: {language}\n"
            f"  Branch: {branch_name}"
        )

        # Step 7: Retry based on task type
        if task_type == "application_build":
            from application.agents.github.tool_definitions.code_generation.tools.generate_application_tool import (
                generate_application,
            )

            result = await generate_application(
                requirements=user_request,
                language=language,
                repository_path=repository_path,
                branch_name=branch_name,
                tool_context=tool_context,
            )

            if result.startswith("✅"):
                return (
                    f"✅ Successfully retried failed application build (original task: {task_id}).\n\n"
                    f"{result}\n\n"
                    f"Original error was: {error_description}"
                )
            else:
                return f"❌ Retry failed with same error:\n\n{result}"

        elif task_type == "code_generation":
            from application.agents.github.tool_definitions.code_generation.tools.generate_code_tool import (
                generate_code_with_cli,
            )

            result = await generate_code_with_cli(
                user_request=user_request,
                tool_context=tool_context,
                language=language,
            )

            if result.startswith("✅"):
                return (
                    f"✅ Successfully retried failed code generation (original task: {task_id}).\n\n"
                    f"{result}\n\n"
                    f"Original error was: {error_description}"
                )
            else:
                return f"❌ Retry failed with same error:\n\n{result}"

        else:
            return (
                f"ERROR: Unknown task type '{task_type}'. "
                f"Only 'application_build' and 'code_generation' tasks can be retried."
            )

    except Exception as e:
        logger.error(f"Failed to retry task {task_id}: {e}", exc_info=True)
        return f"ERROR: Failed to retry task: {str(e)}"


__all__ = ["retry_failed_generation"]
