"""Process and environment monitoring for repository build operations.

REFACTORED: Functionality split into focused modules in monitoring_helpers/:
- environment_status.py: Environment deployment status checking
- output_streaming.py: Process output streaming and task updates
- process_monitoring.py: Build process monitoring with commits

All functions are re-exported below for 100% backward compatibility.
"""

from __future__ import annotations

import logging

from services.services import get_task_service
from common.utils.utils import send_get_request

logger = logging.getLogger(__name__)

# Re-export all public functions from split modules
from .monitoring_helpers import (
    # Environment status constants
    DEFAULT_CLIENT_HOST,
    GUEST_USER_PREFIX,
    MOCK_MODE_ENV_VAR,
    NO_TOOL_CONTEXT_ERROR,
    NEEDS_LOGIN_STATUS,
    DEPLOYED_STATUS_TEMPLATE,
    NOT_DEPLOYED_STATUS_TEMPLATE,
    DEPLOYING_STATUS_TEMPLATE,
    ERROR_STATUS_TEMPLATE,
    # Output streaming constants
    STREAM_READ_CHUNK_SIZE,
    STREAM_READ_TIMEOUT_SECONDS,
    UPDATE_INTERVAL_SECONDS,
    UPDATE_SIZE_THRESHOLD,
    KEEP_LAST_OUTPUT_BYTES,
    # Data classes
    EnvironmentStatusContext,
    OutputStreamState,
    # Environment status functions
    _extract_status_context,
    _construct_environment_url,
    _store_environment_info,
    _check_environment_deployed,
    check_user_environment_status,
    # Output streaming functions
    _read_process_output_chunk,
    _should_update_task,
    _update_task_with_output,
    _stream_process_output,
    # Process monitoring functions
    _extract_auth_info,
    _send_initial_commit,
    _handle_process_completion,
    _handle_periodic_commit,
    _update_task_with_commit_info,
    _handle_timeout_exceeded,
    _monitor_build_process,
    _terminate_process,
)

__all__ = [
    # Service dependencies (for test mocking)
    "get_task_service",
    "send_get_request",
    "logger",
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
