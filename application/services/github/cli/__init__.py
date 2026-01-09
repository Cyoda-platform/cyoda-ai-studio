"""CLI operations module - backward compatibility re-exports."""

from .monitor import (
    _build_completion_metadata,
    _check_process_running,
    _handle_failure_completion,
    _handle_success_completion,
    _perform_final_commit,
    _perform_initial_commit,
    _perform_periodic_commit,
    _unregister_process,
    _update_progress_status,
)
from .utils import (
    _create_output_log_file,
    _create_prompt_file,
    _extract_repo_metadata,
    _finalize_output_file,
    _register_process_and_create_task,
    _start_subprocess,
    _write_log_header,
)
from .validation import (
    _validate_cli_inputs,
    _validate_cli_provider_config,
    _validate_script_path,
)

__all__ = [
    # Validation
    "_validate_cli_inputs",
    "_validate_script_path",
    "_validate_cli_provider_config",
    # Utils
    "_create_prompt_file",
    "_create_output_log_file",
    "_write_log_header",
    "_start_subprocess",
    "_finalize_output_file",
    "_register_process_and_create_task",
    "_extract_repo_metadata",
    # Monitor
    "_perform_initial_commit",
    "_check_process_running",
    "_perform_periodic_commit",
    "_update_progress_status",
    "_unregister_process",
    "_perform_final_commit",
    "_build_completion_metadata",
    "_handle_success_completion",
    "_handle_failure_completion",
]
