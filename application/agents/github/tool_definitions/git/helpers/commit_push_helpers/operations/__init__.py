"""Git operations for staging, committing, and pushing changes.

This module handles the core git operations including staging files,
getting diffs, committing changes, and pushing to remote.

The module is organized into focused submodules:
- diff_operations: Diff parsing and categorization
- git_commands: Individual git command execution
- workflow: High-level workflow coordination
"""

from __future__ import annotations

# Re-export all public APIs from submodules
from .diff_operations import (
    DiffResult,
    _parse_diff_line,
    _categorize_diff_changes,
    _get_staged_diff,
)

from .git_commands import (
    _stage_all_changes,
    _configure_git_user,
    _commit_changes,
    _get_current_remote_url,
    _push_changes,
)

from .workflow import (
    _execute_commit_push_workflow,
    _commit_and_push_changes,
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
