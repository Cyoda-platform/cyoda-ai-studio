"""Commit and push helper functions split into focused modules.

This package organizes commit and push functionality into:
- authentication: Auth extraction, validation, URL refresh
- operations: Git operations (stage, diff, commit, push)

All functions are re-exported from the main module for backward compatibility.
"""

from .authentication import (
    CommitContext,
    _extract_auth_from_context,
    _validate_auth_params,
    _get_authenticated_url_with_timeout,
    _update_git_remote_url,
    _refresh_git_authentication,
)

from .operations import (
    DiffResult,
    _stage_all_changes,
    _parse_diff_line,
    _categorize_diff_changes,
    _get_staged_diff,
    _configure_git_user,
    _commit_changes,
    _get_current_remote_url,
    _push_changes,
    _execute_commit_push_workflow,
    _commit_and_push_changes,
)

__all__ = [
    # Data classes
    "CommitContext",
    "DiffResult",
    # Authentication functions
    "_extract_auth_from_context",
    "_validate_auth_params",
    "_get_authenticated_url_with_timeout",
    "_update_git_remote_url",
    "_refresh_git_authentication",
    # Operation functions
    "_stage_all_changes",
    "_parse_diff_line",
    "_categorize_diff_changes",
    "_get_staged_diff",
    "_configure_git_user",
    "_commit_changes",
    "_get_current_remote_url",
    "_push_changes",
    "_execute_commit_push_workflow",
    "_commit_and_push_changes",
]
