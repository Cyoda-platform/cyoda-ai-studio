"""Deployment monitoring utilities.

This module handles deployment progress monitoring and status updates,
separating monitoring concerns from the main deployment logic.
"""

from __future__ import annotations

# Re-export dependencies (for test mocking)
from services.services import get_task_service

# Re-export all public components
from .status_checks import (
    DeploymentStatus,
    StatusCheckContext,
    _parse_status_result,
    _calculate_progress,
    _is_failure_status,
    _is_success_state,
    _build_deployment_status,
)
from .task_updates import (
    _update_task_failed,
    _update_task_completed,
    _update_task_progress,
    _get_task_info,
)
from .deployment_handling import (
    _handle_failure,
    _handle_success,
    _handle_progress,
    _handle_status_check,
    _check_deployment_status_once,
    monitor_deployment_progress,
)

__all__ = [
    # Dependencies (for test mocking)
    "get_task_service",
    # Status checks
    "DeploymentStatus",
    "StatusCheckContext",
    "_parse_status_result",
    "_calculate_progress",
    "_is_failure_status",
    "_is_success_state",
    "_build_deployment_status",
    # Task updates
    "_update_task_failed",
    "_update_task_completed",
    "_update_task_progress",
    "_get_task_info",
    # Deployment handling
    "_handle_failure",
    "_handle_success",
    "_handle_progress",
    "_handle_status_check",
    "_check_deployment_status_once",
    "monitor_deployment_progress",
]
