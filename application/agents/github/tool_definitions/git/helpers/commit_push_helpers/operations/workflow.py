"""High-level workflow coordination for commit and push operations.

This module orchestrates the complete commit and push workflow by coordinating
individual git commands and handling authentication.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.utils import (
    ensure_repository_available,
)

from ..authentication import (
    CommitContext,
    _extract_auth_from_context,
    _validate_auth_params,
    _refresh_git_authentication,
)
from .diff_operations import DiffResult, _get_staged_diff
from .git_commands import (
    _stage_all_changes,
    _configure_git_user,
    _commit_changes,
    _get_current_remote_url,
    _push_changes,
)

logger = logging.getLogger(__name__)


async def _execute_commit_push_workflow(
    repository_path_str: str, branch_name: str, repo_url: Optional[str], installation_id: Optional[str]
) -> tuple[bool, DiffResult, Optional[str]]:
    """Execute the commit and push workflow steps.

    Args:
        repository_path_str: Repository path
        branch_name: Branch name
        repo_url: Repository URL
        installation_id: GitHub App installation ID

    Returns:
        Tuple of (push_success, diff_result, error_msg)
    """
    # Step 1: Refresh authentication if credentials available
    if repo_url and installation_id:
        await _refresh_git_authentication(repository_path_str, repo_url, installation_id)

    # Step 2: Stage all changes
    await _stage_all_changes(repository_path_str)

    # Step 3: Get diff before committing
    diff_result = await _get_staged_diff(repository_path_str)

    # Step 4: Configure git user
    await _configure_git_user(repository_path_str)

    # Step 5: Commit changes
    await _commit_changes(repository_path_str, branch_name)

    # Step 6: Check remote URL
    await _get_current_remote_url(repository_path_str)

    # Step 7: Push changes
    push_success, push_error = await _push_changes(repository_path_str, branch_name)

    return push_success, diff_result, push_error if not push_success else None


async def _commit_and_push_changes(
    repository_path: str,
    branch_name: str,
    tool_context: Optional[ToolContext] = None,
    repo_url: Optional[str] = None,
    installation_id: Optional[str] = None,
    repository_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Commit and push all changes in the repository.

    Uses GitHub App authentication to refresh credentials before push.
    Internal helper for monitoring tasks.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Optional tool context for extracting auth info
        repo_url: Optional repository URL
        installation_id: Optional GitHub App installation ID
        repository_type: Optional repository type - "public" or "private"

    Returns:
        Dict with status and message
    """
    try:
        repository_path_str = str(repository_path)
        logger.info(
            f"📝 _commit_and_push_changes START - repo: {repository_path_str}, "
            f"branch: {branch_name}"
        )

        # Step 1: Ensure repository is available locally
        success, message, repository_path_str = await ensure_repository_available(
            repository_path=repository_path_str,
            tool_context=tool_context,
            require_git=True,
        )

        if not success:
            error_msg = f"❌ Repository availability check failed: {message}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        # Step 2: Build context and extract authentication info
        context = CommitContext(
            repository_path=repository_path_str,
            branch_name=branch_name,
            tool_context=tool_context,
            repo_url=repo_url,
            installation_id=installation_id,
            repository_type=repository_type,
        )

        repository_type, repo_url, installation_id = _extract_auth_from_context(context)

        # Step 3: Validate authentication parameters
        is_valid, error_msg = _validate_auth_params(
            repository_type, repo_url, installation_id
        )
        if not is_valid:
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        # Step 4: Execute commit and push workflow
        push_success, diff_result, push_error = await _execute_commit_push_workflow(
            repository_path_str, branch_name, repo_url, installation_id
        )

        # Step 5: Return result based on push status
        if push_success:
            logger.info(f"💾 Progress commit pushed for branch {branch_name}")
            return {
                "status": "success",
                "message": "Changes committed and pushed",
                "changed_files": diff_result.changed_files,
                "diff": diff_result.diff_summary,
            }

        logger.error(f"❌ Push failed: {push_error}")
        return {
            "status": "error",
            "message": f"Push failed: {push_error}",
            "changed_files": diff_result.changed_files,
            "diff": diff_result.diff_summary,
        }

    except Exception as e:
        logger.error(f"❌ Failed to commit/push: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
