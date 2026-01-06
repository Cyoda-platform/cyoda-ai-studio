"""CLI helper functions split into focused modules.

This package organizes CLI functionality into:
- context_extraction: Context and data structures
- validation: Parameter and state validation
- file_management: File and output management
- process_management: Process and task management
- monitoring: Monitoring task functions

All functions are re-exported from the main module for backward compatibility.
"""

from .context_extraction import (
    BackgroundTaskData,
    CLIContext,
    CLIProcessInfo,
    _extract_context_values,
)

from .validation import (
    _validate_cli_parameters,
    _extract_cli_context,
    _check_build_already_started,
    _validate_branch_not_protected,
    _validate_cli_invocation_limit,
)

from .file_management import (
    _write_prompt_to_tempfile,
    _create_output_log_file,
    _rename_output_file_with_pid,
)

from .process_management import (
    INITIAL_TASK_PROGRESS,
    TASK_RUNNING_STATUS,
    TASK_RUNNING_MESSAGE_TEMPLATE,
    TASK_CREATED_LOG,
    TASK_UPDATED_LOG,
    CONVERSATION_ADD_ERROR,
    DEFAULT_REPOSITORY_OWNER,
    REPOSITORY_URL_TEMPLATES,
    _start_cli_process,
    _build_repository_url,
    _build_task_data,
    _save_background_task,
    _update_background_task_status,
    _add_task_to_conversation_safe,
    _create_background_task,
)

from .monitoring import (
    _start_monitoring_task,
)

__all__ = [
    # Data classes
    "BackgroundTaskData",
    "CLIContext",
    "CLIProcessInfo",
    # Constants
    "INITIAL_TASK_PROGRESS",
    "TASK_RUNNING_STATUS",
    "TASK_RUNNING_MESSAGE_TEMPLATE",
    "TASK_CREATED_LOG",
    "TASK_UPDATED_LOG",
    "CONVERSATION_ADD_ERROR",
    "DEFAULT_REPOSITORY_OWNER",
    "REPOSITORY_URL_TEMPLATES",
    # Context extraction
    "_extract_context_values",
    # Validation
    "_validate_cli_parameters",
    "_extract_cli_context",
    "_check_build_already_started",
    "_validate_branch_not_protected",
    "_validate_cli_invocation_limit",
    # File management
    "_write_prompt_to_tempfile",
    "_create_output_log_file",
    "_rename_output_file_with_pid",
    # Process management
    "_start_cli_process",
    "_build_repository_url",
    "_build_task_data",
    "_save_background_task",
    "_update_background_task_status",
    "_add_task_to_conversation_safe",
    "_create_background_task",
    # Monitoring
    "_start_monitoring_task",
]
