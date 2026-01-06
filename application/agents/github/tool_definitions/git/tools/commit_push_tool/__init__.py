"""Tool for committing and pushing changes to the repository.

This module handles committing and pushing changes to the repository,
including authentication refresh and canvas hook creation.
"""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.hooks.hook_decorator import creates_hook

# Re-export all components
from .context import (
    GitConfiguration,
    _validate_and_extract_context,
    _prepare_repository_and_git,
    get_entity_service,
)
from .git_operations import (
    _configure_git_user,
    _stage_all_changes,
    _is_nothing_to_commit,
    _commit_changes,
    _configure_git_and_commit,
    _push_to_branch,
)
from .authentication import (
    _get_repo_url_and_installation_id,
    _update_remote_url,
    _refresh_auth_and_push,
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
    repository_path: str, branch_name: str, commit_message: str, tool_context: ToolContext
) -> tuple[bool, str]:
    """Execute commit and push operations.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        commit_message: Commit message
        tool_context: Tool context

    Returns:
        Tuple of (success, error_message)
    """
    success, error_msg, _, changed_files = await _prepare_repository_and_git(
        repository_path, tool_context
    )
    if not success:
        return False, error_msg

    success, error_msg = await _configure_git_and_commit(repository_path, commit_message)
    if not success or error_msg:
        return False, error_msg

    success, error_msg = await _refresh_auth_and_push(repository_path, branch_name, tool_context)
    if not success:
        return False, error_msg

    return True, ""


def _build_canvas_hook_response(
    conversation_id: str,
    repository_name: str,
    repository_owner: str,
    branch_name: str,
    changed_files: list,
    commit_message: str,
    canvas_resources: dict,
    tool_context: ToolContext,
) -> str:
    """Build response with canvas hook if resources changed.

    Args:
        conversation_id: Conversation ID
        repository_name: Repository name
        repository_owner: Repository owner
        branch_name: Branch name
        changed_files: List of changed files
        commit_message: Commit message
        canvas_resources: Canvas resources detected
        tool_context: Tool context

    Returns:
        Response message with hook
    """
    from application.agents.shared.hooks.hook_utils import (
        create_code_changes_hook,
        wrap_response_with_hook,
    )

    if not canvas_resources or not changed_files:
        return f"SUCCESS: Changes committed and pushed to branch {branch_name}"

    hook = create_code_changes_hook(
        conversation_id=conversation_id,
        repository_name=repository_name,
        branch_name=branch_name,
        changed_files=changed_files,
        commit_message=commit_message,
        resources=canvas_resources,
        repository_owner=repository_owner,
    )
    tool_context.state["last_tool_hook"] = hook
    message = (
        f"✅ Changes committed and pushed to branch {branch_name}\n\n"
        "📊 Canvas resources updated - click 'Open Canvas' to view changes."
    )
    return wrap_response_with_hook(message, hook)


@creates_hook("code_changes")
async def commit_and_push_changes(
    commit_message: str, tool_context: ToolContext
) -> str:
    """Commit and push all changes to the conversation's repository branch.

    Args:
        commit_message: Commit message describing the changes
        tool_context: The ADK tool context

    Returns:
        Success or error message with optional canvas analysis hook
    """
    try:
        (
            success, error_msg, repository_path, branch_name, conversation_id
        ) = await _validate_and_extract_context(tool_context)
        if not success:
            return error_msg

        success, error_msg = await _execute_commit_and_push(
            repository_path, branch_name, commit_message, tool_context
        )
        if not success:
            return error_msg

        logger.info(f"Committed and pushed changes to branch {branch_name}: {commit_message}")

        from application.agents.shared.hooks.hook_utils import detect_canvas_resources

        success, _, repository_path, changed_files = await _prepare_repository_and_git(
            repository_path, tool_context
        )
        canvas_resources = detect_canvas_resources(changed_files) if success else {}
        repository_name = tool_context.state.get("repository_name")
        repository_owner = tool_context.state.get("repository_owner")

        return _build_canvas_hook_response(
            conversation_id, repository_name, repository_owner, branch_name,
            changed_files, commit_message, canvas_resources, tool_context
        )

    except Exception as e:
        logger.error(f"Error committing and pushing changes: {e}", exc_info=True)
        return f"ERROR: {str(e)}"
