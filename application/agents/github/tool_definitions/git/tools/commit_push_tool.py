"""Tool for committing and pushing changes to the repository.

This module handles committing and pushing changes to the repository,
including authentication refresh and canvas hook creation.

All implementation has been moved to commit_push_tool/ subdirectory.
This file maintains backward compatibility by re-exporting all components.
"""

from __future__ import annotations

# Re-export all public components for backward compatibility
from .commit_push_tool import (
    GitConfiguration,
    _validate_and_extract_context,
    _prepare_repository_and_git,
    _configure_git_user,
    _stage_all_changes,
    _is_nothing_to_commit,
    _commit_changes,
    _configure_git_and_commit,
    _push_to_branch,
    _get_repo_url_and_installation_id,
    _update_remote_url,
    _refresh_auth_and_push,
    commit_and_push_changes,
)

__all__ = [
    "GitConfiguration",
    "_validate_and_extract_context",
    "_prepare_repository_and_git",
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
