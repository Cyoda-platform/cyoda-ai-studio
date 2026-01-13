"""File operations for repository management - saving files to branches and repositories.

All implementation has been moved to files/ subdirectory.
This file maintains backward compatibility by re-exporting all components.
"""

# Re-export all public components for backward compatibility
from .files import (
    _add_files_to_git,
    _check_git_status,
    _commit_and_push_files,
    _commit_files_to_git,
    _configure_git_user,
    _determine_functional_requirements_dir,
    _log_directory_debug_info,
    _push_to_remote,
    _save_all_files,
    _save_file_to_disk,
    _update_remote_authentication,
    _validate_files_input,
    _validate_tool_context_state,
    save_files_to_branch,
)

__all__ = [
    "_validate_files_input",
    "_validate_tool_context_state",
    "_determine_functional_requirements_dir",
    "_save_file_to_disk",
    "_log_directory_debug_info",
    "_save_all_files",
    "_configure_git_user",
    "_add_files_to_git",
    "_check_git_status",
    "_commit_files_to_git",
    "_update_remote_authentication",
    "_push_to_remote",
    "_commit_and_push_files",
    "save_files_to_branch",
]
