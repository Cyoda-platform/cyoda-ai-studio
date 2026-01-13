"""Tool for generating code using CLI based on user requests.

This module provides incremental code generation for existing repositories.

The module is organized into focused submodules:
- validation: Context, repository, and configuration validation
- process_management: Process startup, registration, and monitoring
- tool_execution: Main tool function and response formatting
"""

from __future__ import annotations

# Re-export dependencies (for test mocking)
from common.config.config import CLI_PROVIDER

from .process_management import (
    _create_and_setup_background_task,
    _start_and_register_process,
)
from .tool_execution import (
    generate_code_with_cli,
)

# Re-export all public APIs from submodules
from .validation import (
    AUGMENT_CLI_SUPPORTED_MODEL,
    SUPPORTED_LANGUAGES,
    _validate_and_prepare_context,
    _validate_repository_and_config,
)

__all__ = [
    # Dependencies (for test mocking)
    "CLI_PROVIDER",
    # Constants
    "SUPPORTED_LANGUAGES",
    "AUGMENT_CLI_SUPPORTED_MODEL",
    # Validation
    "_validate_and_prepare_context",
    "_validate_repository_and_config",
    # Process management
    "_start_and_register_process",
    "_create_and_setup_background_task",
    # Tool execution
    "generate_code_with_cli",
]
