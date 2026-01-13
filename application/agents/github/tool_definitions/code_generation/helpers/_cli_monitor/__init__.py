"""Helper for monitoring CLI processes.

This module provides functionality to monitor CLI processes (code generation and builds),
updating BackgroundTask entities with progress and committing changes periodically.
"""

from __future__ import annotations

# Re-export all public components
from application.agents.github.tool_definitions.git import _commit_and_push_changes
from application.agents.github.tool_definitions.repository import get_repository_diff

from .commit_operations import (
    AuthInfo,
    _commit_progress,
    _extract_auth_info,
    _get_diff_summary,
    _send_final_commit,
    _send_initial_commit,
)
from .process_monitoring import (
    MonitorConfig,
    _handle_normal_completion,
    _handle_periodic_updates,
    _handle_process_timeout,
    _unregister_process,
    monitor_cli_process,
)
from .task_updates import (
    _handle_process_timeout_task_update,
    _update_task_on_completion,
    _update_task_progress,
    _update_task_with_commit_info,
)

__all__ = [
    # Git operations
    "_commit_and_push_changes",
    "get_repository_diff",
    # Commit operations
    "AuthInfo",
    "_extract_auth_info",
    "_get_diff_summary",
    "_send_initial_commit",
    "_send_final_commit",
    "_commit_progress",
    # Task updates
    "_update_task_on_completion",
    "_update_task_progress",
    "_update_task_with_commit_info",
    "_handle_process_timeout_task_update",
    # Process monitoring
    "MonitorConfig",
    "_unregister_process",
    "_handle_normal_completion",
    "_handle_periodic_updates",
    "_handle_process_timeout",
    "monitor_cli_process",
]
