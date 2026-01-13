"""
Repository tools module - refactored into focused sub-modules.

This module provides a clean public API while organizing code into logical components.
"""

# Import from cli_process
from .cli_process import (
    setup_and_monitor_cli_process,
    start_cli_process,
)

# Import constants
from .constants import (
    AUGMENT_CLI_SCRIPT,
    DEFAULT_BUILD_TIMEOUT_SECONDS,
    GITHUB_PUBLIC_REPO_INSTALLATION_ID,
    INITIAL_RETRY_DELAY_SECONDS,
    JAVA_PUBLIC_REPO_URL,
    JAVA_TEMPLATE_REPO,
    MAX_LOCK_RETRIES,
    MAX_RETRY_DELAY_SECONDS,
    OUTPUT_UPDATE_SIZE_THRESHOLD,
    OUTPUT_UPDATE_TIME_THRESHOLD_SECONDS,
    PROCESS_CHECK_INTERVAL_SECONDS,
    PROCESS_COMMIT_INTERVAL_SECONDS,
    PROCESS_KILL_GRACE_SECONDS,
    PYTHON_PUBLIC_REPO_URL,
    PYTHON_TEMPLATE_REPO,
    UNKNOWN_ERROR_MESSAGE,
)

# Import from conversation
from .conversation import (
    _add_task_to_conversation,
    _update_conversation_build_context,
    _update_conversation_with_lock,
    retrieve_and_save_conversation_files,
)

# Import from files
from .files import (
    save_files_to_branch,
)

# Import from generation
from .generation import (
    _load_prompt_template,
    check_build_status,
    generate_application,
    wait_before_next_check,
)

# Import from git_operations
from .git_operations import (
    _get_authenticated_repo_url_sync,
    _get_git_diff,
    _run_git_command,
)

# Import from monitoring
from .monitoring import (
    _monitor_build_process,
    _stream_process_output,
    _terminate_process,
    check_user_environment_status,
)

# Import from repository
from .repository import (
    _extract_repo_name_and_owner,
    _get_repository_config_from_context,
    check_existing_branch_configuration,
    clone_repository,
    generate_branch_uuid,
    set_repository_config,
)

# Import from validation
from .validation import (
    _is_protected_branch,
    _validate_clone_parameters,
)

# Legacy imports kept for backward compatibility during migration
# (all other functions have been migrated to focused modules)

__all__ = [
    # Constants
    "AUGMENT_CLI_SCRIPT",
    "DEFAULT_BUILD_TIMEOUT_SECONDS",
    "GITHUB_PUBLIC_REPO_INSTALLATION_ID",
    "INITIAL_RETRY_DELAY_SECONDS",
    "JAVA_PUBLIC_REPO_URL",
    "JAVA_TEMPLATE_REPO",
    "MAX_LOCK_RETRIES",
    "MAX_RETRY_DELAY_SECONDS",
    "OUTPUT_UPDATE_SIZE_THRESHOLD",
    "OUTPUT_UPDATE_TIME_THRESHOLD_SECONDS",
    "PROCESS_CHECK_INTERVAL_SECONDS",
    "PROCESS_COMMIT_INTERVAL_SECONDS",
    "PROCESS_KILL_GRACE_SECONDS",
    "PYTHON_PUBLIC_REPO_URL",
    "PYTHON_TEMPLATE_REPO",
    "UNKNOWN_ERROR_MESSAGE",
    # Git operations
    "_get_authenticated_repo_url_sync",
    "_get_git_diff",
    "_run_git_command",
    # Validation
    "_is_protected_branch",
    "_validate_clone_parameters",
    # Repository operations
    "_extract_repo_name_and_owner",
    "_get_repository_config_from_context",
    "check_existing_branch_configuration",
    "clone_repository",
    "generate_branch_uuid",
    "set_repository_config",
    # Application generation
    "_load_prompt_template",
    "check_build_status",
    "generate_application",
    "wait_before_next_check",
    # File operations
    "retrieve_and_save_conversation_files",
    "save_files_to_branch",
    # Process monitoring
    "_monitor_build_process",
    "_stream_process_output",
    "_terminate_process",
    "start_cli_process",
    "setup_and_monitor_cli_process",
    # Conversation operations
    "_add_task_to_conversation",
    "_update_conversation_build_context",
    "_update_conversation_with_lock",
    # Prompts/UI
    "check_user_environment_status",
]
