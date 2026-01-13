"""Git operations for staging, committing, and pushing changes.

This is a compatibility wrapper that re-exports all functionality from the
operations package. The actual implementation has been refactored into focused
modules within the operations/ subdirectory for better maintainability.

For new code, consider importing directly from:
- operations.diff_operations: Diff parsing and categorization
- operations.git_commands: Individual git command execution
- operations.workflow: High-level workflow coordination
"""

from __future__ import annotations

# Re-export all public APIs for backward compatibility
from .operations import (  # Data classes; Diff operations; Git commands; Workflow
    DiffResult,
    _categorize_diff_changes,
    _commit_and_push_changes,
    _commit_changes,
    _configure_git_user,
    _execute_commit_push_workflow,
    _get_current_remote_url,
    _get_staged_diff,
    _parse_diff_line,
    _push_changes,
    _stage_all_changes,
)

__all__ = [
    # Data classes
    "DiffResult",
    # Diff operations
    "_parse_diff_line",
    "_categorize_diff_changes",
    "_get_staged_diff",
    # Git commands
    "_stage_all_changes",
    "_configure_git_user",
    "_commit_changes",
    "_get_current_remote_url",
    "_push_changes",
    # Workflow
    "_execute_commit_push_workflow",
    "_commit_and_push_changes",
]
