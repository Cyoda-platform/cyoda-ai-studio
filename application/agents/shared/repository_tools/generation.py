"""
Application generation and build management functions.

This module handles:
- User interaction for option selection
- Application generation via Augment CLI
- Build status monitoring and tracking
- Prompt template management

Internal organization:
- operations/validation.py: Validation functions
- operations/utils.py: Utility functions
- operations/build.py: Build process management
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict

from google.adk.tools.tool_context import ToolContext
from services.services import get_task_service

from application.agents.shared.hooks import (
    create_option_selection_hook,
    wrap_response_with_hook,
)
from application.agents.shared.tool_context_helpers import get_conversation_id
from application.agents.shared.repository_tools.constants import (
    PROTECTED_BRANCHES,
)
from application.agents.shared.repository_tools.validation import (
    _is_protected_branch,
)
# Re-export from operations modules for backward compatibility
from .operations import (
    validate_and_prepare_build_wrapper as _validate_and_prepare_build_impl,
    _extract_context_params,
    _validate_build_not_in_progress,
    _validate_required_params,
    _verify_repository,
    _validate_tool_context,
    _validate_question,
    _validate_options,
    _get_requirements_directory_path,
    _check_requirements_exist,
    _build_augment_command,
    _build_repository_url,
    _format_success_response as _format_utils_response,
    _load_prompt_template,
    DEFAULT_REPOSITORY_NAME,
    PYTHON_REPO_NAME,
    JAVA_REPO_NAME,
    AUGMENT_CLI_SCRIPT,
    _start_and_register_process,
    _deploy_environment_if_needed,
    _create_build_task,
    _start_background_monitoring,
    _validate_build_environment as _validate_build_environment_impl,
    _prepare_build_command as _prepare_build_command_impl,
    _start_build_process as _start_build_process_impl,
    _setup_build_tracking as _setup_build_tracking_impl,
)

logger = logging.getLogger(__name__)


async def ask_user_to_select_option(
    question: str,
    options: list[Dict[str, str]],
    selection_type: str = "single",
    context: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Show interactive UI for the user to select from a list of options.

    This is a generic tool that can be used whenever you need to ask the user to choose from multiple options.
    The UI will display clickable buttons or checkboxes for the user to make their selection.

    **CRITICAL PATTERN - YOU MUST ALWAYS PROVIDE THE 'options' PARAMETER:**
    This tool REQUIRES the 'options' parameter. You MUST provide a list of at least one option.
    Each option MUST be a dictionary with 'value' and 'label' fields.
    NEVER call this tool without the 'options' parameter.
    Example: options=[{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}]

    Args:
        question: The question to ask the user (required, cannot be empty)
        options: List of option dictionaries with 'value' and 'label' fields (required)
        selection_type: Either "single" (radio buttons) or "multiple" (checkboxes). Default: "single"
        context: Optional additional context or information to display
        tool_context: Execution context (auto-injected)

    Returns:
        Message with hook for UI to display selection interface
    """
    _validate_tool_context(tool_context)
    _validate_question(question)
    _validate_options(options)

    # Get conversation_id with fallback to session.id for standalone ADK web mode
    conversation_id = get_conversation_id(tool_context)

    hook = create_option_selection_hook(
        conversation_id=conversation_id,
        question=question,
        options=options,
        selection_type=selection_type,
        context=context,
    )

    tool_context.state["last_tool_hook"] = hook
    message = f"{question}\n\nPlease select your choice(s) using the options below."

    return wrap_response_with_hook(message, hook)


async def generate_application(
    requirements: str,
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    branch_name: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generate application using Augment CLI with comprehensive prompt.

    Uses repository_path, branch_name, and language from tool_context.state if not provided.
    This allows the agent to call generate_application with just requirements after clone_repository.
    Enforces a limit on concurrent CLI processes to prevent resource exhaustion.

    Args:
        requirements: User requirements for the application.
        language: Programming language ('java' or 'python') - optional if in context.
        repository_path: Path to cloned repository - optional if in context.
        branch_name: Branch name for the build - optional if in context.
        tool_context: Execution context (auto-injected).

    Returns:
        Status message with build job ID or error.
    """
    if not requirements:
        raise ValueError("requirements parameter is required and cannot be empty")

    try:
        language, repository_path, branch_name, error_msg = await _validate_and_prepare_build_impl(
            requirements, language, repository_path, branch_name, tool_context
        )
        if error_msg:
            return error_msg

        error_msg = await _validate_build_environment_impl(language, repository_path)
        if error_msg:
            return error_msg

        augment_model = os.getenv("AUGMENT_MODEL", "gemini-pro")
        command, error_msg = await _prepare_build_command_impl(
            language, repository_path, branch_name, augment_model
        )
        if error_msg:
            return error_msg

        # Start build process using shared CLI process starter
        from application.agents.shared.repository_tools.cli_process import start_cli_process

        success, error_msg, process = await start_cli_process(
            command=command,
            repository_path=repository_path,
            process_type="build",
        )
        if not success or not process:
            return error_msg or "Failed to start build process"

        # Setup task tracking and monitoring (build uses legacy flow with helpers)
        build_task_id, env_task_id = await _setup_build_tracking_impl(
            tool_context, language, branch_name, repository_path, requirements, process.pid
        )

        await _start_background_monitoring(process, repository_path, branch_name, tool_context)

        logger.info(
            f"✅ Build started successfully (PID: {process.pid}, Build Task: {build_task_id}, Env Task: {env_task_id})"
        )

        return _format_success_response_public(branch_name, language, build_task_id, env_task_id)

    except Exception as e:
        logger.error(f"❌ Failed to generate application: {e}", exc_info=True)
        return f"ERROR: Failed to generate application: {str(e)}"


def _format_success_response_public(
    branch_name: str,
    language: str,
    build_task_id: Optional[str],
    env_task_id: Optional[str],
) -> str:
    """Format success response with task IDs.

    Args:
        branch_name: Git branch name.
        language: Programming language.
        build_task_id: Build task ID (optional).
        env_task_id: Environment deployment task ID (optional).

    Returns:
        Formatted success message.
    """
    task_ids = []
    if build_task_id:
        task_ids.append(build_task_id)
    if env_task_id:
        task_ids.append(env_task_id)

    base_msg = f"SUCCESS: Build started successfully on branch {branch_name} ({language})."
    setup_msg = "Once the build completes, please call the setup assistant to configure your application."

    if task_ids:
        task_ids_str = ", ".join(task_ids)
        return f"{base_msg} Task IDs: {task_ids_str}. {setup_msg}"
    else:
        return f"{base_msg} Monitoring build progress in background. {setup_msg}"


async def check_build_status(
    build_job_info: str, tool_context: Optional[ToolContext] = None
) -> str:
    """
    Check the status of a build job.

    Args:
        build_job_info: Build job information (format: "job_id|PID:pid|PATH:path")
        tool_context: Execution context (auto-injected)

    Returns:
        Status message in format "ESCALATE: <message>" or "CONTINUE: <message>"
    """
    try:
        # Parse build job info
        parts = build_job_info.split("|")
        if len(parts) < 3:
            return "ESCALATE: Invalid build job info format"

        job_id = parts[0]
        pid_str = parts[1].replace("PID:", "")
        repo_path = parts[2].replace("PATH:", "")

        pid = int(pid_str)

        # Check if process is still running
        try:
            os.kill(pid, 0)  # Signal 0 checks if process exists
            # Process is still running
            logger.info(f"Build job {job_id} (PID: {pid}) is still running")

            # Status is tracked in BackgroundTask entity only
            # No need to send messages to conversation

            return f"CONTINUE: Build job {job_id} is still in progress"
        except OSError:
            # Process has finished
            logger.info(f"Build job {job_id} (PID: {pid}) has completed")

            # Check for build artifacts or success indicators
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                # Status is tracked in BackgroundTask entity only
                return f"ESCALATE: Build completed but repository path {repo_path} not found"

            # Check for common build success indicators
            success_indicators = [
                repo_path_obj / "build" / "libs",  # Java Gradle
                repo_path_obj / "target",  # Java Maven
                repo_path_obj / ".venv",  # Python venv
                repo_path_obj / "dist",  # Python dist
            ]

            has_artifacts = any(indicator.exists() for indicator in success_indicators)

            if has_artifacts:
                # Status is tracked in BackgroundTask entity only
                return f"ESCALATE: Build job {job_id} completed successfully. Artifacts found in {repo_path}"
            else:
                # Status is tracked in BackgroundTask entity only
                return f"ESCALATE: Build job {job_id} completed. Please verify build output in {repo_path}"

    except ValueError:
        logger.error(f"Invalid PID in build job info: {build_job_info}")
        return "ESCALATE: Invalid build job info - could not parse PID"
    except Exception as e:
        logger.error(f"Failed to check build status: {e}", exc_info=True)
        return f"ESCALATE: Error checking build status: {str(e)}"


async def wait_before_next_check(seconds: int = 30) -> str:
    """
    Wait before checking build status again.

    Args:
        seconds: Number of seconds to wait (default: 30)

    Returns:
        Confirmation message
    """
    logger.info(f"Waiting {seconds} seconds before next build status check")
    await asyncio.sleep(seconds)
    return f"Waited {seconds} seconds. Ready for next status check."


__all__ = [
    # Public API
    "ask_user_to_select_option",
    "generate_application",
    "check_build_status",
    "wait_before_next_check",
    # Service dependencies (for test mocking)
    "get_task_service",
    # Re-exported for backward compatibility
    "_extract_context_params",
    "_validate_build_not_in_progress",
    "_validate_required_params",
    "_verify_repository",
    "_validate_tool_context",
    "_validate_question",
    "_validate_options",
    "_get_requirements_directory_path",
    "_check_requirements_exist",
    "_build_augment_command",
    "_build_repository_url",
    "_load_prompt_template",
    "DEFAULT_REPOSITORY_NAME",
    "PYTHON_REPO_NAME",
    "JAVA_REPO_NAME",
    "AUGMENT_CLI_SCRIPT",
    "_start_and_register_process",
    "_deploy_environment_if_needed",
    "_create_build_task",
    "_start_background_monitoring",
]
