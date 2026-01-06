"""Internal handler functions for repository operations.

This module is organized into focused submodules:
- branch_handlers: Branch creation and checkout operations
- clone_operations: Repository cloning and setup
- finalization: Context updates and success messaging
"""

from __future__ import annotations

# Re-export all public APIs from submodules
from .branch_handlers import (
    _handle_new_branch,
    _handle_existing_branch,
    _handle_branch_setup,
)

from .clone_operations import (
    _handle_already_cloned_repo,
    _build_target_path,
    _determine_repo_url,
    _validate_and_check_protected_branch,
    _extract_repo_name_and_owner,
    _setup_repository_clone,
    _perform_clone_and_branch,
    _handle_push_and_finalize,
)

from .finalization import (
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
