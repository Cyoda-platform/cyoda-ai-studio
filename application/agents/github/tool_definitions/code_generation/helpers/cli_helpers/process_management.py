"""Process and task management for CLI operations.

This module handles CLI process startup, background task creation,
and repository URL construction.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

from common.config.config import CLI_PROVIDER

from .context_extraction import BackgroundTaskData, CLIContext

logger = logging.getLogger(__name__)

# Background task constants
INITIAL_TASK_PROGRESS = 5
TASK_RUNNING_STATUS = "running"
TASK_RUNNING_MESSAGE_TEMPLATE = "Process started (PID: {pid})"
TASK_CREATED_LOG = "📋 Created BackgroundTask entity: {task_id}"
TASK_UPDATED_LOG = "📋 Updated BackgroundTask {task_id} to {status}"
CONVERSATION_ADD_ERROR = "Could not add task to conversation: {error}"
DEFAULT_REPOSITORY_OWNER = "Cyoda-platform"
REPOSITORY_URL_TEMPLATES = {
    "python": "https://github.com/{owner}/mcp-cyoda-quart-app/tree/{branch}",
    "java": "https://github.com/{owner}/java-client-template/tree/{branch}",
}


async def _start_cli_process(
    script_path: Path,
    prompt_file: str,
    cli_model: str,
    repository_path: str,
    branch_name: str,
    output_fd: int,
) -> Any:
    """Start CLI subprocess.

    Args:
        script_path: Path to CLI script
        prompt_file: Path to prompt file
        cli_model: CLI model name
        repository_path: Repository path
        branch_name: Branch name
        output_fd: Output file descriptor

    Returns:
        Started subprocess
    """
    cmd = [
        "bash",
        str(script_path.absolute()),
        f"@{prompt_file}",
        cli_model,
        repository_path,
        branch_name,
    ]

    provider_name = CLI_PROVIDER.capitalize()
    logger.info(f"🚀 Starting {provider_name} CLI process...")
    logger.info(f"🎯 Model: {cli_model}")
    logger.info(f"📁 Workspace: {repository_path}")
    logger.info(f"🌿 Branch: {branch_name}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=output_fd,
        stderr=output_fd,
        cwd=repository_path,
    )

    logger.info(f"✅ {provider_name} CLI process started with PID: {process.pid}")
    return process


def _build_repository_url(
    repository_type: Optional[str], language: str, branch_name: str
) -> Optional[str]:
    """Build GitHub repository URL.

    Args:
        repository_type: Repository type
        language: Programming language
        branch_name: Branch name

    Returns:
        Repository URL or None
    """
    if repository_type != "public":
        return None

    if language.lower() == "python":
        repo_name = "mcp-cyoda-quart-app"
    elif language.lower() == "java":
        repo_name = "java-client-template"
    else:
        repo_name = "mcp-cyoda-quart-app"

    repo_owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")
    return f"https://github.com/{repo_owner}/{repo_name}/tree/{branch_name}"


def _build_task_data(
    context: CLIContext,
    task_type: str,
    task_name: str,
    task_description: str,
    repository_url: Optional[str],
) -> BackgroundTaskData:
    """Build background task data structure.

    Args:
        context: CLI context
        task_type: Task type
        task_name: Task name
        task_description: Task description
        repository_url: Repository URL

    Returns:
        BackgroundTaskData object
    """
    return BackgroundTaskData(
        user_id=context.tool_context.state.get("user_id", "CYODA"),
        task_type=task_type,
        name=task_name,
        description=task_description,
        branch_name=context.branch_name,
        language=context.language,
        user_request=context.requirements,
        conversation_id=context.conversation_id,
        repository_path=context.repository_path,
        repository_type=context.repository_type,
        repository_url=repository_url,
    )


async def _save_background_task(
    task_data: BackgroundTaskData,
) -> str:
    """Create background task in service.

    Args:
        task_data: Background task data

    Returns:
        Task ID
    """
    # Local import for test mocking compatibility
    from services.services import get_task_service

    task_service = get_task_service()

    background_task = await task_service.create_task(**task_data.model_dump())

    task_id = background_task.technical_id
    logger.info(TASK_CREATED_LOG.format(task_id=task_id))

    return task_id


async def _update_background_task_status(
    task_id: str,
    process_pid: int,
    output_file: str,
) -> None:
    """Update background task to running status.

    Args:
        task_id: Task ID
        process_pid: Process PID
        output_file: Output log file path
    """
    # Local import for test mocking compatibility
    from services.services import get_task_service

    task_service = get_task_service()

    await task_service.update_task_status(
        task_id=task_id,
        status=TASK_RUNNING_STATUS,
        message=TASK_RUNNING_MESSAGE_TEMPLATE.format(pid=process_pid),
        progress=INITIAL_TASK_PROGRESS,
        process_pid=process_pid,
        metadata={"output_log": output_file},
    )

    logger.info(TASK_UPDATED_LOG.format(task_id=task_id, status=TASK_RUNNING_STATUS))


async def _add_task_to_conversation_safe(
    conversation_id: Optional[str], task_id: str
) -> None:
    """Safely add task to conversation.

    Args:
        conversation_id: Conversation ID
        task_id: Task ID
    """
    if not conversation_id:
        return

    try:
        # Local import for test mocking compatibility
        from application.agents.shared.repository_tools import _add_task_to_conversation

        await _add_task_to_conversation(conversation_id, task_id)
    except Exception as e:
        # Log but don't fail if conversation update fails (e.g., in tests)
        logger.warning(CONVERSATION_ADD_ERROR.format(error=e))


async def _create_background_task(
    context: CLIContext,
    task_type: str,
    task_name: str,
    task_description: str,
    process_pid: int,
    output_file: str,
) -> str:
    """Create background task for tracking.

    Args:
        context: CLI context
        task_type: Task type ("application_build" or "code_generation")
        task_name: Task name
        task_description: Task description
        process_pid: Process PID
        output_file: Output log file path

    Returns:
        Task ID

    Example:
        >>> task_id = await _create_background_task(
        ...     context=cli_context,
        ...     task_type="application_build",
        ...     task_name="Build Application",
        ...     task_description="Building application with Cyoda",
        ...     process_pid=1234,
        ...     output_file="/tmp/build.log"
        ... )
    """
    # Step 1: Build repository URL
    repository_url = _build_repository_url(
        context.repository_type, context.language, context.branch_name
    )

    # Step 2: Build task data structure
    task_data = _build_task_data(
        context, task_type, task_name, task_description, repository_url
    )

    # Step 3: Create task in service
    task_id = await _save_background_task(task_data)

    # Step 4: Update task to running status
    await _update_background_task_status(task_id, process_pid, output_file)

    # Step 5: Store in context
    context.tool_context.state["background_task_id"] = task_id
    context.tool_context.state["output_log"] = output_file

    # Step 6: Add to conversation if applicable
    await _add_task_to_conversation_safe(context.conversation_id, task_id)

    return task_id
