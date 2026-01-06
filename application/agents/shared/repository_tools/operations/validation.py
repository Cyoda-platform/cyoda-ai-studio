"""Validation functions for build generation."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.constants import (
    DEFAULT_BUILD_TIMEOUT_SECONDS,
    PROTECTED_BRANCHES,
)
from application.agents.shared.repository_tools.validation import (
    _is_protected_branch,
)

logger = logging.getLogger(__name__)


async def validate_and_prepare_build_wrapper(
    requirements: str,
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
    tool_context: Optional[ToolContext],
) -> tuple[Optional[str], Optional[str], Optional[str], str]:
    """Validate and prepare all parameters for build generation.

    This is a wrapper function that combines all validation steps needed
    before starting a build.

    Args:
        requirements: Build requirements.
        language: Programming language (optional).
        repository_path: Repository path (optional).
        branch_name: Branch name (optional).
        tool_context: Execution context.

    Returns:
        Tuple of (language, repository_path, branch_name, error_msg).
        If error_msg is not empty, other values may be None.
    """
    # Step 1: Check if build is already in progress
    error_msg = _validate_build_not_in_progress(tool_context)
    if error_msg:
        return None, None, None, error_msg

    # Step 2: Extract context parameters
    language, repository_path, branch_name, repository_name = _extract_context_params(
        language, repository_path, branch_name, tool_context
    )

    # Step 3: Validate required parameters
    error_msg = _validate_required_params(language, repository_path, branch_name)
    if error_msg:
        return language, repository_path, branch_name, error_msg

    # Step 4: Check for protected branch
    if await _is_protected_branch(branch_name):
        error_msg = f"ERROR: Cannot use protected branch '{branch_name}'. Please use a feature branch instead."
        logger.error(error_msg)
        return language, repository_path, branch_name, error_msg

    # Step 5: Verify repository exists
    error_msg = await _verify_repository(repository_path)
    if error_msg:
        return language, repository_path, branch_name, error_msg

    # All validations passed
    return language, repository_path, branch_name, ""


def _extract_context_params(
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
    tool_context: Optional[ToolContext],
) -> tuple[Optional[str], Optional[str], Optional[str], str]:
    """Extract and normalize context parameters.

    Args:
        language: Programming language (optional).
        repository_path: Repository path (optional).
        branch_name: Branch name (optional).
        tool_context: Execution context.

    Returns:
        Tuple of (language, repository_path, branch_name, repository_name).
    """
    DEFAULT_REPOSITORY_NAME = "mcp-cyoda-quart-app"
    repository_name = DEFAULT_REPOSITORY_NAME
    if tool_context:
        language = language or tool_context.state.get("language")
        repository_path = repository_path or tool_context.state.get("repository_path")
        branch_name = branch_name or tool_context.state.get("branch_name")
        repository_name = tool_context.state.get("repository_name", repository_name)

        logger.info(
            f"🔍 Context state: language={language}, repository_path={repository_path}, "
            f"branch_name={branch_name}, repository_name={repository_name}"
        )

    return language, repository_path, branch_name, repository_name


def _validate_build_not_in_progress(tool_context: Optional[ToolContext]) -> str:
    """Check if a build is already in progress.

    Args:
        tool_context: Execution context.

    Returns:
        Empty string if no build in progress, error message otherwise.
    """
    if not tool_context:
        return ""

    existing_build_pid = tool_context.state.get("build_process_pid")
    existing_branch = tool_context.state.get("branch_name")

    if existing_build_pid and existing_branch:
        msg = f"⚠️ Build already started for branch {existing_branch} (PID: {existing_build_pid})"
        logger.warning(msg)
        return f"{msg}. Please wait for it to complete."

    return ""


def _validate_required_params(
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
) -> str:
    """Validate required parameters are provided.

    Args:
        language: Programming language.
        repository_path: Repository path.
        branch_name: Branch name.

    Returns:
        Empty string if valid, error message otherwise.
    """
    if not language:
        logger.error("Language not specified and not found in context")
        return "ERROR: Language not specified and not found in context. Please call clone_repository first."
    if not repository_path:
        logger.error("Repository path not specified and not found in context")
        return "ERROR: Repository path not specified and not found in context. Please call clone_repository first."
    if not branch_name:
        logger.error("Branch name not specified and not found in context")
        return "ERROR: Branch name not specified and not found in context. Please call clone_repository first."

    return ""


async def _verify_repository(repository_path: str) -> str:
    """Verify repository directory exists and is a git repository.

    Args:
        repository_path: Path to repository.

    Returns:
        Empty string if valid, error message otherwise.
    """
    repo_path = Path(repository_path)
    if not repo_path.exists():
        logger.error(f"Repository directory does not exist: {repository_path}")
        return (
            f"ERROR: Repository directory does not exist: {repository_path}. "
            f"Please call clone_repository first."
        )

    if not (repo_path / ".git").exists():
        logger.error(f"Directory exists but is not a git repository: {repository_path}")
        return (
            f"ERROR: Directory exists but is not a git repository: {repository_path}. "
            "Please call clone_repository first."
        )

    logger.info(f"✅ Repository verified at: {repository_path}")
    return ""


def _validate_tool_context(tool_context: Optional[ToolContext]) -> None:
    """Validate tool context is available.

    Args:
        tool_context: Execution context.

    Raises:
        ValueError: If tool context is None.
    """
    if not tool_context:
        raise ValueError("Tool context not available. This function must be called within a conversation context.")


def _validate_question(question: str) -> None:
    """Validate question parameter.

    Args:
        question: Question text.

    Raises:
        ValueError: If question is empty.
    """
    if not question or not question.strip():
        raise ValueError("The 'question' parameter is required")


def _validate_options(options: list[Dict[str, str]]) -> None:
    """Validate options list format.

    Args:
        options: List of option dictionaries.

    Raises:
        ValueError: If options is invalid.
    """
    if not options or len(options) == 0:
        raise ValueError("The 'options' parameter is required and must contain at least one option")

    for i, option in enumerate(options):
        if not isinstance(option, dict):
            raise ValueError(f"Option at index {i} is not a dictionary")
        if "value" not in option:
            raise ValueError(f"Option at index {i} is missing required 'value' field")
        if "label" not in option:
            raise ValueError(f"Option at index {i} is missing required 'label' field")
