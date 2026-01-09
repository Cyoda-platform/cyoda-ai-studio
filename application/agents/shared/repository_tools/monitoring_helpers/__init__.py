"""Repository monitoring helpers split into focused modules.

This package organizes monitoring functionality into:
- environment_status: Environment deployment status checking
- output_streaming: Process output streaming and task updates
- process_monitoring: Build process monitoring with commits

All functions are re-exported from the main module for backward compatibility.
"""

from .environment_status import (
    DEFAULT_CLIENT_HOST,
    DEPLOYED_STATUS_TEMPLATE,
    DEPLOYING_STATUS_TEMPLATE,
    ERROR_STATUS_TEMPLATE,
    GUEST_USER_PREFIX,
    MOCK_MODE_ENV_VAR,
    NEEDS_LOGIN_STATUS,
    NO_TOOL_CONTEXT_ERROR,
    NOT_DEPLOYED_STATUS_TEMPLATE,
    EnvironmentStatusContext,
    _check_environment_deployed,
    _construct_environment_url,
    _extract_status_context,
    _store_environment_info,
    check_user_environment_status,
)
from .output_streaming import (
    KEEP_LAST_OUTPUT_BYTES,
    STREAM_READ_CHUNK_SIZE,
    STREAM_READ_TIMEOUT_SECONDS,
    UPDATE_INTERVAL_SECONDS,
    UPDATE_SIZE_THRESHOLD,
    OutputStreamState,
    _read_process_output_chunk,
    _should_update_task,
    _stream_process_output,
    _update_task_with_output,
)
from .process_monitoring import (
    _extract_auth_info,
    _handle_periodic_commit,
    _handle_process_completion,
    _handle_timeout_exceeded,
    _monitor_build_process,
    _send_initial_commit,
    _terminate_process,
    _update_task_with_commit_info,
)

__all__ = [
    # Environment status constants
    "DEFAULT_CLIENT_HOST",
    "GUEST_USER_PREFIX",
    "MOCK_MODE_ENV_VAR",
    "NO_TOOL_CONTEXT_ERROR",
    "NEEDS_LOGIN_STATUS",
    "DEPLOYED_STATUS_TEMPLATE",
    "NOT_DEPLOYED_STATUS_TEMPLATE",
    "DEPLOYING_STATUS_TEMPLATE",
    "ERROR_STATUS_TEMPLATE",
    # Output streaming constants
    "STREAM_READ_CHUNK_SIZE",
    "STREAM_READ_TIMEOUT_SECONDS",
    "UPDATE_INTERVAL_SECONDS",
    "UPDATE_SIZE_THRESHOLD",
    "KEEP_LAST_OUTPUT_BYTES",
    # Data classes
    "EnvironmentStatusContext",
    "OutputStreamState",
    # Environment status functions
    "_extract_status_context",
    "_construct_environment_url",
    "_store_environment_info",
    "_check_environment_deployed",
    "check_user_environment_status",
    # Output streaming functions
    "_read_process_output_chunk",
    "_should_update_task",
    "_update_task_with_output",
    "_stream_process_output",
    # Process monitoring functions
    "_extract_auth_info",
    "_send_initial_commit",
    "_handle_process_completion",
    "_handle_periodic_commit",
    "_update_task_with_commit_info",
    "_handle_timeout_exceeded",
    "_monitor_build_process",
    "_terminate_process",
]
