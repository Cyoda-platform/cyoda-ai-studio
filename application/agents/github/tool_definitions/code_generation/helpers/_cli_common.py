"""Shared helpers for CLI code generation and build operations.

This module contains common logic shared between generate_application and generate_code_with_cli.

REFACTORED: Functionality split into focused modules in cli_helpers/:
- context_extraction.py: Context and data structures
- validation.py: Parameter and state validation
- file_management.py: File and output management
- process_management.py: Process and task management
- monitoring.py: Monitoring task functions

All functions are re-exported below for 100% backward compatibility.
"""

from __future__ import annotations

# Re-export all public functions from split modules
from .cli_helpers import (  # Data classes; Constants; Context extraction; Validation; File management; Process management; Monitoring
    CONVERSATION_ADD_ERROR,
    DEFAULT_REPOSITORY_OWNER,
    INITIAL_TASK_PROGRESS,
    REPOSITORY_URL_TEMPLATES,
    TASK_CREATED_LOG,
    TASK_RUNNING_MESSAGE_TEMPLATE,
    TASK_RUNNING_STATUS,
    TASK_UPDATED_LOG,
    BackgroundTaskData,
    CLIContext,
    CLIProcessInfo,
    _add_task_to_conversation_safe,
    _build_repository_url,
    _build_task_data,
    _check_build_already_started,
    _create_background_task,
    _create_output_log_file,
    _extract_cli_context,
    _extract_context_values,
    _rename_output_file_with_pid,
    _save_background_task,
    _start_cli_process,
    _start_monitoring_task,
    _update_background_task_status,
    _validate_branch_not_protected,
    _validate_cli_invocation_limit,
    _validate_cli_parameters,
    _write_prompt_to_tempfile,
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
