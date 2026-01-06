"""Repository utility functions for common operations.

This module provides reusable helpers for repository operations to avoid
code duplication across tool definitions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def _check_repository_exists(repository_path: str, require_git: bool) -> bool:
    """Check if repository exists locally.

    Args:
        repository_path: Path to repository
        require_git: Whether to require .git directory

    Returns:
        True if repository exists, False otherwise
    """
    repo_path_obj = Path(repository_path)

    if require_git:
        return repo_path_obj.exists() and (repo_path_obj / ".git").exists()

    return repo_path_obj.exists()


def _extract_clone_parameters(tool_context: ToolContext) -> tuple[str, str, str | None, str | None, str | None]:
    """Extract clone parameters from tool context.

    Args:
        tool_context: Tool context

    Returns:
        Tuple of (repository_url, branch_name, installation_id, repository_name, repository_owner)
    """
    repository_url = tool_context.state.get("user_repository_url") or tool_context.state.get("repository_url")
    installation_id = tool_context.state.get("installation_id")
    branch_name = tool_context.state.get("branch_name")
    repository_name = tool_context.state.get("repository_name")
    repository_owner = tool_context.state.get("repository_owner")

    return repository_url, branch_name, installation_id, repository_name, repository_owner


async def _clone_repository(
    repository_url: str,
    branch_name: str,
    installation_id: str | None,
    repository_name: str | None,
    repository_owner: str | None,
) -> tuple[bool, str, str]:
    """Clone repository using provided parameters.

    Args:
        repository_url: Repository URL
        branch_name: Branch name
        installation_id: Installation ID
        repository_name: Repository name
        repository_owner: Repository owner

    Returns:
        Tuple of (success, message, cloned_path)
    """
    from application.routes.repository_routes import _ensure_repository_cloned

    success, message, cloned_path = await _ensure_repository_cloned(
        repository_url=repository_url,
        repository_branch=branch_name,
        installation_id=installation_id,
        repository_name=repository_name,
        repository_owner=repository_owner,
        use_env_installation_id=True,
    )

    return success, message, cloned_path


async def ensure_repository_available(
    repository_path: str,
    tool_context: Optional[ToolContext] = None,
    require_git: bool = True,
) -> Tuple[bool, str, str]:
    """Ensure repository is available locally, cloning if necessary.

    This function checks if a repository exists locally and has a .git directory
    (if required). If not found, it attempts to clone the repository using
    authentication information from the tool context.

    Args:
        repository_path: Path where repository should be located
        tool_context: Tool context containing repository URL and auth info
        require_git: Whether to require a .git directory (default: True)

    Returns:
        Tuple of (success: bool, message: str, actual_path: str)
        - success: True if repository is available, False otherwise
        - message: Error message if success=False, success message otherwise
        - actual_path: Actual path to repository (may differ if cloned)
    """
    if _check_repository_exists(repository_path, require_git):
        logger.debug(f"Repository already available at {repository_path}")
        return True, "Repository available", repository_path

    logger.info(f"📦 Repository not found at {repository_path}, attempting to clone...")

    if not tool_context:
        error_msg = f"Repository not available at {repository_path} and no tool_context provided for cloning"
        logger.error(error_msg)
        return False, error_msg, repository_path

    repository_url, branch_name, installation_id, repository_name, repository_owner = (
        _extract_clone_parameters(tool_context)
    )

    if not repository_url or not branch_name:
        error_msg = (
            f"Repository not available and insufficient information to clone. "
            f"repository_url: {repository_url}, branch: {branch_name}"
        )
        logger.error(error_msg)
        return False, error_msg, repository_path

    try:
        success, message, cloned_path = await _clone_repository(
            repository_url, branch_name, installation_id, repository_name, repository_owner
        )

        if not success:
            error_msg = f"Failed to clone repository: {message}"
            logger.error(error_msg)
            return False, error_msg, repository_path

        logger.info(f"✅ Repository cloned successfully at {cloned_path}")
        return True, "Repository cloned successfully", cloned_path

    except Exception as e:
        error_msg = f"Exception during repository clone: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, repository_path
