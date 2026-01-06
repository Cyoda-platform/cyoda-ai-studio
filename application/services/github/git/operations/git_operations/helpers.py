"""Helper functions for GitOperations class."""

import logging
from typing import Optional

from pydantic import BaseModel

from common.config.config import PROJECT_DIR
from application.services.github.models.types import GitOperationResult

logger = logging.getLogger(__name__)

DEFAULT_MERGE_STRATEGY = "recursive"
NO_CHANGES_TO_PULL_MSG = "No changes to pull"
NOTHING_TO_COMMIT_MSG = "nothing to commit"


class GitOperationState(BaseModel):
    """State container for git operation context."""

    clone_dir: str
    git_branch_id: str
    merge_strategy: str = DEFAULT_MERGE_STRATEGY


def get_clone_dir(git_branch_id: str, repository_name: str) -> str:
    """Get clone directory path.

    Args:
        git_branch_id: Branch ID
        repository_name: Repository name (used as directory name)

    Returns:
        Full path to clone directory
    """
    return f"{PROJECT_DIR}/{git_branch_id}/{repository_name}"


def build_branch_result(
    success: bool, error_msg: Optional[str], git_branch_id: str
) -> GitOperationResult:
    """Build GitOperationResult for branch operations.

    Args:
        success: Whether operation succeeded
        error_msg: Error message if any
        git_branch_id: Branch ID

    Returns:
        GitOperationResult with appropriate message
    """
    if not success:
        return GitOperationResult(
            success=False, message="Branch operation failed", error=error_msg
        )

    message = (
        f"Checked out branch {git_branch_id}"
        if error_msg is None
        else f"Created branch {git_branch_id}"
    )
    return GitOperationResult(success=True, message=message)


def build_pull_result(
    had_changes: bool, diff_result: str, error_msg: Optional[str] = None
) -> GitOperationResult:
    """Build GitOperationResult for pull operations.

    Args:
        had_changes: Whether there were changes to pull
        diff_result: Diff output
        error_msg: Error message if any

    Returns:
        GitOperationResult with appropriate message
    """
    if error_msg:
        return GitOperationResult(success=False, message="Pull failed", error=error_msg)

    if not had_changes:
        return GitOperationResult(
            success=True,
            message=NO_CHANGES_TO_PULL_MSG,
            had_changes=False,
            diff=diff_result,
        )

    return GitOperationResult(
        success=True, message="Pull successful", had_changes=True, diff=diff_result
    )


def build_push_result(
    success: bool, message: str, error_msg: Optional[str] = None
) -> GitOperationResult:
    """Build GitOperationResult for push operations.

    Args:
        success: Whether operation succeeded
        message: Success message
        error_msg: Error message if any

    Returns:
        GitOperationResult with appropriate message
    """
    if error_msg:
        return GitOperationResult(success=False, message=message, error=error_msg)

    return GitOperationResult(success=True, message=message)


def should_skip_commit(error_msg: Optional[str]) -> bool:
    """Check if commit should be skipped (nothing to commit).

    Args:
        error_msg: Error message from commit operation

    Returns:
        True if nothing to commit
    """
    return error_msg == NOTHING_TO_COMMIT_MSG
