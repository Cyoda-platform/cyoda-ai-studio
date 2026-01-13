"""Tool for committing and pushing changes to the repository.

This module handles committing and pushing changes to the repository,
including authentication refresh.
"""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

from .authentication import (
    _get_repo_url_and_installation_id,
    _refresh_auth_and_push,
    _update_remote_url,
)

# Re-export all components
from .context import (
    GitConfiguration,
    _prepare_repository_and_git,
    _validate_and_extract_context,
    get_entity_service,
)
from .git_operations import (
    _commit_changes,
    _configure_git_and_commit,
    _configure_git_user,
    _is_nothing_to_commit,
    _push_to_branch,
    _stage_all_changes,
)

__all__ = [
    "GitConfiguration",
    "_validate_and_extract_context",
    "_prepare_repository_and_git",
    "get_entity_service",
    "_configure_git_user",
    "_stage_all_changes",
    "_is_nothing_to_commit",
    "_commit_changes",
    "_configure_git_and_commit",
    "_push_to_branch",
    "_get_repo_url_and_installation_id",
    "_update_remote_url",
    "_refresh_auth_and_push",
    "commit_and_push_changes",
]

logger = logging.getLogger(__name__)


async def _execute_commit_and_push(
    repository_path: str,
    branch_name: str,
    commit_message: str,
    tool_context: ToolContext,
) -> tuple[bool, str, list]:
    """Execute commit and push operations.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        commit_message: Commit message
        tool_context: Tool context

    Returns:
        Tuple of (success, error_message, changed_files)
    """
    success, error_msg, _, changed_files = await _prepare_repository_and_git(
        repository_path, tool_context
    )
    if not success:
        return False, error_msg, []

    success, commit_msg = await _configure_git_and_commit(
        repository_path, commit_message
    )
    if not success:
        return False, commit_msg, []

    # If nothing to commit, return early (don't push)
    if commit_msg and "No changes to commit" in commit_msg:
        return True, commit_msg, []

    success, error_msg = await _refresh_auth_and_push(
        repository_path, branch_name, tool_context
    )
    if not success:
        return False, error_msg, []

    return True, "", changed_files


async def commit_and_push_changes(
    commit_message: str, tool_context: ToolContext
) -> str:
    """Commit and push all changes to the conversation's repository branch.

    Args:
        commit_message: Commit message describing the changes
        tool_context: The ADK tool context

    Returns:
        Success or error message
    """
    try:
        (success, error_msg, repository_path, branch_name, conversation_id) = (
            await _validate_and_extract_context(tool_context)
        )
        if not success:
            return error_msg

        success, error_msg, changed_files = await _execute_commit_and_push(
            repository_path, branch_name, commit_message, tool_context
        )
        if not success:
            return error_msg

        # If nothing to commit, return early with the message
        if error_msg and "No changes to commit" in error_msg:
            return error_msg

        logger.info(
            f"Committed and pushed changes to branch {branch_name}: {commit_message}"
        )

        # Return plain success message - UI will detect canvas resources from tool execution
        return f"✅ Changes committed and pushed to branch {branch_name}"

    except Exception as e:
        logger.error(f"Error committing and pushing changes: {e}", exc_info=True)
        return f"ERROR: {str(e)}"
