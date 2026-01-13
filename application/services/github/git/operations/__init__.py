"""Git operations module for local repository management.

This is a compatibility wrapper that re-exports all functionality from the
operations package. The actual implementation has been refactored into focused
modules within the operations/ subdirectory for better maintainability.

This package is organized into focused modules:
- url_management: Repository URL construction with authentication
- branch_management: Branch operations (checkout, create, track)
- local_operations: File staging, commits, pushes, pulls, clone
- git_operations: Main GitOperations class coordinating all operations

For new code, consider importing directly from the submodules as needed.
"""

from __future__ import annotations

# Re-export result types from models
from application.services.github.models.types import GitOperationResult
from common.config.config import CLONE_REPO

from .branch_management import (
    checkout_base_and_create_branch,
    checkout_branch_if_exists,
    create_branch_from_base,
    ensure_branch_exists,
    set_upstream_tracking,
)

# Re-export main classes
from .git_operations import (
    GitOperations,
    GitOperationState,
)
from .local_operations import (
    DEFAULT_MERGE_STRATEGY,
    NO_CHANGES_TO_PULL_MSG,
    NOTHING_TO_COMMIT_MSG,
    add_files_to_git,
    commit_changes,
    configure_pull_strategy,
    perform_git_clone,
    push_to_remote,
    repo_exists,
    run_git_config,
    run_git_diff,
    run_git_fetch,
    run_git_pull,
)

# Re-export submodule functions
from .url_management import get_repository_url

__all__ = [
    # Config constants (for test mocking)
    "CLONE_REPO",
    # URL management
    "get_repository_url",
    # Branch management
    "checkout_branch_if_exists",
    "create_branch_from_base",
    "checkout_base_and_create_branch",
    "set_upstream_tracking",
    "ensure_branch_exists",
    # Local operations
    "add_files_to_git",
    "commit_changes",
    "push_to_remote",
    "run_git_fetch",
    "run_git_diff",
    "configure_pull_strategy",
    "run_git_pull",
    "perform_git_clone",
    "run_git_config",
    "repo_exists",
    "DEFAULT_MERGE_STRATEGY",
    "NO_CHANGES_TO_PULL_MSG",
    "NOTHING_TO_COMMIT_MSG",
    # Main classes
    "GitOperationState",
    "GitOperations",
    # Result types
    "GitOperationResult",
]
