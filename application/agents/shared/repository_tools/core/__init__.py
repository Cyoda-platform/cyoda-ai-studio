"""Repository core module - backward compatibility re-exports."""

import uuid

from .config import (
    JAVA_REPO_NAME,
    PYTHON_REPO_NAME,
    BranchConfiguration,
    _build_invalid_repo_type_error,
    _build_missing_context_error,
    _build_no_config_error,
    _detect_language,
    _determine_repository_type,
    _extract_config_from_conversation,
    _extract_config_from_tool_state,
    _get_private_repo_config,
    _get_public_repo_config,
    _get_repository_config_from_context,
    _validate_tool_context,
)
from .context import (
    _store_in_tool_context,
    _update_conversation_build_context_wrapper,
    _update_conversation_entity,
)
from .git_ops import (
    _checkout_existing_branch,
    _clone_repo_to_path,
    _create_new_branch,
    _push_branch_to_remote,
)
from .handlers import (
    _build_target_path,
    _determine_repo_url,
    _extract_repo_name_and_owner,
    _finalize_clone,
    _format_clone_success_message,
    _handle_already_cloned_repo,
    _handle_branch_setup,
    _handle_existing_branch,
    _handle_new_branch,
    _handle_push_and_finalize,
    _perform_clone_and_branch,
    _setup_repository_clone,
    _validate_and_check_protected_branch,
)

__all__ = [
    # Config
    "BranchConfiguration",
    "_validate_tool_context",
    "_extract_config_from_tool_state",
    "_extract_config_from_conversation",
    "_detect_language",
    "_determine_repository_type",
    "_get_private_repo_config",
    "_get_public_repo_config",
    "PYTHON_REPO_NAME",
    "JAVA_REPO_NAME",
    # Errors
    "_build_missing_context_error",
    "_build_no_config_error",
    "_build_invalid_repo_type_error",
    # Git ops
    "_clone_repo_to_path",
    "_checkout_existing_branch",
    "_create_new_branch",
    "_push_branch_to_remote",
    # Context
    "_store_in_tool_context",
    "_update_conversation_entity",
    "_update_conversation_build_context_wrapper",
    # Handlers
    "_handle_already_cloned_repo",
    "_handle_new_branch",
    "_handle_existing_branch",
    "_build_target_path",
    "_determine_repo_url",
    "_validate_and_check_protected_branch",
    "_extract_repo_name_and_owner",
    "_setup_repository_clone",
    "_handle_branch_setup",
    "_finalize_clone",
    "_format_clone_success_message",
    "_perform_clone_and_branch",
    "_handle_push_and_finalize",
]
