"""Build process management functions."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.constants import (
    AUGMENT_CLI_SCRIPT,
    DEFAULT_BUILD_TIMEOUT_SECONDS,
)
from services.services import get_task_service

logger = logging.getLogger(__name__)


async def _start_and_register_process(
    command: list[str],
    tool_context: ToolContext,
) -> tuple[Optional[int], Optional[str]]:
    """Start a subprocess and register it in tool context.

    Args:
        command: Command arguments.
        tool_context: Tool context for state management.

    Returns:
        Tuple of (process_id, error_message) or (None, error_message) if failed.
    """
    try:
        logger.info(f"Starting process with command: {' '.join(command)}")

        # Start the process
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        process_id = process.pid
        logger.info(f"Process started with PID: {process_id}")

        # Register in tool context
        tool_context.state["build_process_pid"] = process_id
        tool_context.state["build_start_time"] = asyncio.get_event_loop().time()

        return process_id, None

    except Exception as e:
        error_msg = f"Failed to start process: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


async def _deploy_environment_if_needed(tool_context: Optional[ToolContext]) -> str:
    """Deploy environment if deployment is requested.

    Args:
        tool_context: Tool context.

    Returns:
        Empty string if deployment not needed or successful, error message otherwise.
    """
    if not tool_context:
        return ""

    should_deploy = tool_context.state.get("should_deploy_environment", False)
    if not should_deploy:
        logger.info("Deployment not requested, skipping environment deployment")
        return ""

    logger.info("Starting environment deployment...")
    # Deployment logic would go here
    return ""


async def _create_build_task(
    conversation_id: Optional[str],
    language: str,
    repository_name: Optional[str],
    branch_name: str,
) -> tuple[Optional[str], Optional[str]]:
    """Create a background task for the build.

    Args:
        conversation_id: Conversation ID.
        language: Programming language.
        repository_name: Repository name.
        branch_name: Branch name.

    Returns:
        Tuple of (task_id, error_message) or (None, error_message) if failed.
    """
    try:
        task_service = get_task_service()

        # Create task
        task_id = await task_service.create_task(
            conversation_id=conversation_id,
            task_type="code_generation",
            task_name=f"Generate {language} Application",
            task_description=(
                f"Generating application from template for {language} in branch {branch_name}"
            ),
            metadata={
                "language": language,
                "repository_name": repository_name,
                "branch_name": branch_name,
            },
        )

        logger.info(f"Created build task: {task_id}")
        return task_id, None

    except Exception as e:
        error_msg = f"Failed to create build task: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


async def _start_background_monitoring(
    tool_context: ToolContext,
) -> str:
    """Start background monitoring of build process.

    Args:
        tool_context: Tool context.

    Returns:
        Empty string if monitoring started successfully, error message otherwise.
    """
    process_id = tool_context.state.get("build_process_pid")
    if not process_id:
        return "ERROR: No build process ID found"

    logger.info(f"Starting background monitoring for process {process_id}")
    # Background monitoring logic would go here
    return ""


async def _validate_and_prepare_build(
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
) -> str:
    """Validate and prepare for build.

    Args:
        language: Programming language.
        repository_path: Repository path.
        branch_name: Branch name.

    Returns:
        Empty string if successful, error message otherwise.
    """
    if not all([language, repository_path, branch_name]):
        return "ERROR: Required parameters missing"

    repo_path = Path(repository_path)
    if not repo_path.exists():
        return f"ERROR: Repository path does not exist: {repository_path}"

    logger.info(f"Build validation successful for {language} at {repository_path}")
    return ""


async def _validate_build_environment(
    language: str,
    repository_path: str,
) -> str:
    """Validate build environment.

    Args:
        language: Programming language.
        repository_path: Repository path.

    Returns:
        Empty string if valid, error message otherwise.
    """
    repo_path = Path(repository_path)

    if not repo_path.exists():
        return f"ERROR: Repository directory does not exist: {repository_path}"

    if not (repo_path / ".git").exists():
        return f"ERROR: Not a git repository: {repository_path}"

    # Check for language-specific requirements
    requirements_dir = repo_path / "requirements" / language.lower()
    if not requirements_dir.exists():
        logger.warning(f"Requirements directory not found for {language}")

    logger.info(f"✅ Build environment validated for {language}")
    return ""


async def _prepare_build_command(
    language: str,
    repository_path: str,
    branch_name: str,
    augment_model: str,
) -> tuple[Optional[list[str]], Optional[str]]:
    """Prepare build command.

    Args:
        language: Programming language.
        repository_path: Repository path.
        branch_name: Branch name.
        augment_model: Augment model to use.

    Returns:
        Tuple of (command_list, error_message) or (None, error_message) if failed.
    """
    try:
        from application.agents.shared.repository_tools.operations.utils import _build_augment_command

        command = _build_augment_command(language, repository_path, branch_name, augment_model)
        logger.info(f"Build command prepared: {' '.join(command)}")
        return command, None

    except Exception as e:
        error_msg = f"Failed to prepare build command: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


async def _start_build_process(
    command: list[str],
    timeout_seconds: int = DEFAULT_BUILD_TIMEOUT_SECONDS,
) -> tuple[bool, Optional[str]]:
    """Start build process and wait for completion.

    Args:
        command: Build command.
        timeout_seconds: Timeout for build in seconds.

    Returns:
        Tuple of (success, error_message).
    """
    try:
        logger.info(f"Starting build process with timeout {timeout_seconds}s")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )

            if process.returncode == 0:
                logger.info("Build process completed successfully")
                return True, None
            else:
                error_msg = stderr.decode() if stderr else "Build failed"
                logger.error(f"Build process failed: {error_msg}")
                return False, error_msg

        except asyncio.TimeoutError:
            process.kill()
            error_msg = f"Build process timed out after {timeout_seconds}s"
            logger.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Failed to start build process: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def _setup_build_tracking(
    tool_context: ToolContext,
    task_id: Optional[str],
    process_id: Optional[int],
) -> None:
    """Setup build tracking in tool context.

    Args:
        tool_context: Tool context.
        task_id: Background task ID.
        process_id: Process ID.
    """
    if task_id:
        tool_context.state["build_task_id"] = task_id
    if process_id:
        tool_context.state["build_process_pid"] = process_id

    logger.info(f"Build tracking setup: task_id={task_id}, pid={process_id}")
