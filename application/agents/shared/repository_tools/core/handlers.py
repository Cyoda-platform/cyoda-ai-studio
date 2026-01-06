"""Internal handler functions for repository operations.

This is a compatibility wrapper that re-exports all functionality from the
handlers package. The actual implementation has been refactored into focused
modules within the handlers/ subdirectory for better maintainability.

For new code, consider importing directly from:
- handlers.branch_handlers: Branch creation and checkout
- handlers.clone_operations: Repository cloning and setup
- handlers.finalization: Context updates and success messaging
"""

from __future__ import annotations

# Re-export all public APIs for backward compatibility
from .handlers import (
    # Branch handlers
    _handle_new_branch,
    _handle_existing_branch,
    _handle_branch_setup,
    # Clone operations
    _handle_already_cloned_repo,
    _build_target_path,
    _determine_repo_url,
    _validate_and_check_protected_branch,
    _extract_repo_name_and_owner,
    _setup_repository_clone,
    _perform_clone_and_branch,
    _handle_push_and_finalize,
    # Finalization
    _finalize_clone,
    _format_clone_success_message,
)

__all__ = [
    # Branch handlers
    "_handle_new_branch",
    "_handle_existing_branch",
    "_handle_branch_setup",
    # Clone operations
    "_handle_already_cloned_repo",
    "_build_target_path",
    "_determine_repo_url",
    "_validate_and_check_protected_branch",
    "_extract_repo_name_and_owner",
    "_setup_repository_clone",
    "_perform_clone_and_branch",
    "_handle_push_and_finalize",
    # Finalization
    "_finalize_clone",
    "_format_clone_success_message",
]
