"""Internal helpers for code generation operations."""

# Application build helpers
from ._application_build_helpers import (
    _build_full_prompt,
    _check_functional_requirements_exist,
    _create_missing_requirements_message,
    _load_build_prompt_template,
    _load_pattern_catalog,
)

# Deprecated - use monitor_cli_process directly with appropriate parameters
from ._build_monitor import monitor_build_process

# Shared CLI helpers
from ._cli_common import (
    CLIContext,
    CLIProcessInfo,
    _build_repository_url,
    _check_build_already_started,
    _create_background_task,
    _create_output_log_file,
    _extract_cli_context,
    _rename_output_file_with_pid,
    _start_cli_process,
    _start_monitoring_task,
    _validate_branch_not_protected,
    _validate_cli_invocation_limit,
    _write_prompt_to_tempfile,
)
from ._cli_monitor import monitor_cli_process

# Core code generation logic
from ._code_generation_core import (
    APPLICATION_BUILD_CONFIG,
    CODE_GENERATION_CONFIG,
    CodeGenerationConfig,
    _generate_code_core,
)
from ._process_monitor import monitor_code_generation_process
from ._prompt_loader import load_informational_prompt_template
from ._temp_file_cleanup import cleanup_temp_files, log_temp_file_preserved

# Hooks removed - UI auto-detects build/deployment operations


__all__ = [
    "load_informational_prompt_template",
    "monitor_cli_process",
    "log_temp_file_preserved",
    "cleanup_temp_files",  # Deprecated, use log_temp_file_preserved
    "monitor_code_generation_process",  # Deprecated, use monitor_cli_process
    "monitor_build_process",  # Deprecated, use monitor_cli_process
    # Shared CLI helpers
    "CLIContext",
    "CLIProcessInfo",
    "_extract_cli_context",
    "_check_build_already_started",
    "_validate_branch_not_protected",
    "_validate_cli_invocation_limit",
    "_write_prompt_to_tempfile",
    "_create_output_log_file",
    "_rename_output_file_with_pid",
    "_start_cli_process",
    "_build_repository_url",
    "_create_background_task",
    "_start_monitoring_task",
    # Application build helpers
    "_check_functional_requirements_exist",
    "_create_missing_requirements_message",
    "_load_build_prompt_template",
    "_load_pattern_catalog",
    "_build_full_prompt",
    # Core code generation logic
    "_generate_code_core",
    "APPLICATION_BUILD_CONFIG",
    "CODE_GENERATION_CONFIG",
    "CodeGenerationConfig",
]
