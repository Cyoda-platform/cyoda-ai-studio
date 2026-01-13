"""Deployment monitoring utilities.

This module handles deployment progress monitoring and status updates,
separating monitoring concerns from the main deployment logic.

All implementation has been moved to _deployment_monitor/ subdirectory.
This file maintains backward compatibility by re-exporting all components.
"""

from __future__ import annotations

# Re-export all public components for backward compatibility
from ._deployment_monitor import (
    DeploymentStatus,
    StatusCheckContext,
    _build_deployment_status,
    _calculate_progress,
    _check_deployment_status_once,
    _get_task_info,
    _handle_failure,
    _handle_progress,
    _handle_status_check,
    _handle_success,
    _is_failure_status,
    _is_success_state,
    _parse_status_result,
    _update_task_completed,
    _update_task_failed,
    _update_task_progress,
    monitor_deployment_progress,
)

__all__ = [
    "DeploymentStatus",
    "StatusCheckContext",
    "_parse_status_result",
    "_calculate_progress",
    "_is_failure_status",
    "_is_success_state",
    "_build_deployment_status",
    "_update_task_failed",
    "_update_task_completed",
    "_update_task_progress",
    "_get_task_info",
    "_handle_failure",
    "_handle_success",
    "_handle_progress",
    "_handle_status_check",
    "_check_deployment_status_once",
    "monitor_deployment_progress",
]
