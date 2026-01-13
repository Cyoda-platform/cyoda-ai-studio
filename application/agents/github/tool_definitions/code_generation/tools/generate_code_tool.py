"""Tool for generating code using CLI based on user requests.

This is a compatibility wrapper that re-exports all functionality from the
generate_code_tool package. The actual implementation has been refactored into
focused modules within the generate_code_tool/ subdirectory for better maintainability.

For new code, consider importing directly from:
- generate_code_tool.validation: Context and repository validation
- generate_code_tool.process_management: Process and monitoring setup
- generate_code_tool.tool_execution: Main tool function
"""

from __future__ import annotations

# Re-export all public APIs for backward compatibility
from .generate_code_tool import (  # Constants; Validation; Process management; Tool execution
    AUGMENT_CLI_SUPPORTED_MODEL,
    SUPPORTED_LANGUAGES,
    CodeGenState,
    _create_and_setup_background_task,
    _format_response,
    _start_and_register_process,
    _validate_and_prepare_context,
    _validate_repository_and_config,
    generate_code_with_cli,
)

__all__ = [
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
    "CodeGenState",
    "_format_response",
    "generate_code_with_cli",
]
