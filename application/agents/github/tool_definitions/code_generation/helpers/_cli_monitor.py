"""Helper for monitoring CLI processes.

This module provides functionality to monitor CLI processes (code generation and builds),
updating BackgroundTask entities with progress and committing changes periodically.

All implementation has been moved to _cli_monitor/ subdirectory.
This file maintains backward compatibility by re-exporting all components.
"""

from __future__ import annotations

# Re-export all public components for backward compatibility
from ._cli_monitor import (
    AuthInfo,
    MonitorConfig,
    _extract_auth_info,
    _get_diff_summary,
    _send_initial_commit,
    _send_final_commit,
    _commit_progress,
    _update_task_on_completion,
    _update_task_progress,
    _update_task_with_commit_info,
    _handle_process_timeout_task_update,
    _unregister_process,
    _handle_normal_completion,
    _handle_periodic_updates,
    _handle_process_timeout,
    monitor_cli_process,
)

__all__ = [
    "AuthInfo",
    "MonitorConfig",
    "_extract_auth_info",
    "_get_diff_summary",
    "_send_initial_commit",
    "_send_final_commit",
    "_commit_progress",
    "_update_task_on_completion",
    "_update_task_progress",
    "_update_task_with_commit_info",
    "_handle_process_timeout_task_update",
    "_unregister_process",
    "_handle_normal_completion",
    "_handle_periodic_updates",
    "_handle_process_timeout",
    "monitor_cli_process",
]
