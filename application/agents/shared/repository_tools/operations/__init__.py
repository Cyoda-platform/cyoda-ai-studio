"""Build operations module - backward compatibility re-exports."""

from .validation import (
    validate_and_prepare_build_wrapper,
    _extract_context_params,
    _validate_build_not_in_progress,
    _validate_required_params,
    _verify_repository,
    _validate_tool_context,
    _validate_question,
    _validate_options,
)
from .utils import (
    _get_requirements_directory_path,
    _check_requirements_exist,
    _build_augment_command,
    _build_repository_url,
    _format_success_response,
    _load_prompt_template,
    DEFAULT_REPOSITORY_NAME,
    PYTHON_REPO_NAME,
    JAVA_REPO_NAME,
)
from .build import (
    _start_and_register_process,
    _deploy_environment_if_needed,
    _create_build_task,
    _start_background_monitoring,
    _validate_and_prepare_build,
    _validate_build_environment,
    _prepare_build_command,
    _start_build_process,
    _setup_build_tracking,
    AUGMENT_CLI_SCRIPT,
)

__all__ = [
    # Validation
    "validate_and_prepare_build_wrapper",
    "_extract_context_params",
    "_validate_build_not_in_progress",
    "_validate_required_params",
    "_verify_repository",
    "_validate_tool_context",
    "_validate_question",
    "_validate_options",
    # Utils
    "_get_requirements_directory_path",
    "_check_requirements_exist",
    "_build_augment_command",
    "_build_repository_url",
    "_format_success_response",
    "_load_prompt_template",
    "DEFAULT_REPOSITORY_NAME",
    "PYTHON_REPO_NAME",
    "JAVA_REPO_NAME",
    # Build
    "AUGMENT_CLI_SCRIPT",
    "_start_and_register_process",
    "_deploy_environment_if_needed",
    "_create_build_task",
    "_start_background_monitoring",
    "_validate_and_prepare_build",
    "_validate_build_environment",
    "_prepare_build_command",
    "_start_build_process",
    "_setup_build_tracking",
]
