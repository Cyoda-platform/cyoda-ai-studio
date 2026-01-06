"""Status parsing and checking for deployment monitoring."""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Status check constants
FAILURE_STATUSES = ["UNKNOWN", "FAILURE", "FAILED", "ERROR"]
FAILURE_STATES = ["FAILED", "ERROR"]
SUCCESS_STATES = ["COMPLETE", "SUCCESS", "FINISHED"]
DONE_FLAG = "DONE"
CONTINUE_FLAG = "CONTINUE"
STATUS_PREFIX = "STATUS:"
STATUS_SEPARATOR = "|"
PROGRESS_MIN = 10
PROGRESS_MAX = 95
PROGRESS_STEP = 85


class DeploymentStatus(BaseModel):
    """Deployment status from check result."""

    state: str
    status: str
    done_flag: str
    is_failure: bool = False
    is_success: bool = False


class StatusCheckContext(BaseModel):
    """Context for status check operation."""

    task_id: str
    build_id: str
    check_num: int
    max_checks: int
    namespace: Optional[str] = None
    env_url: Optional[str] = None


def _parse_status_result(status_result: str) -> Optional[tuple[str, str, str]]:
    """Parse status result string.

    Args:
        status_result: Status result string in format "STATUS:state|status|DONE/CONTINUE"

    Returns:
        Tuple of (state, status, done_flag) or None if parsing fails
    """
    if not status_result.startswith("STATUS:"):
        return None

    parts = status_result.replace("STATUS:", "").split("|")
    if len(parts) < 3:
        return None

    return parts[0], parts[1], parts[2]


def _calculate_progress(check_num: int, max_checks: int, done_flag: str) -> int:
    """Calculate deployment progress percentage.

    Args:
        check_num: Current check number
        max_checks: Maximum number of checks
        done_flag: "DONE" or "CONTINUE"

    Returns:
        Progress percentage (0-100)
    """
    if done_flag == "DONE":
        return 100
    # Linear progress from 10% to 95% over max_checks
    return min(95, 10 + int((check_num / max_checks) * 85))


def _is_failure_status(state: str, status: str) -> bool:
    """Check if status indicates failure.

    Args:
        state: Deployment state
        status: Deployment status

    Returns:
        True if status indicates failure
    """
    failure_statuses = ["UNKNOWN", "FAILURE", "FAILED", "ERROR"]
    failure_states = ["FAILED", "ERROR"]

    return (
        status.upper() in failure_statuses or
        state.upper() in failure_states
    )


def _is_success_state(state: str) -> bool:
    """Check if state indicates success.

    Args:
        state: Deployment state

    Returns:
        True if state indicates success
    """
    return state.upper() in ["COMPLETE", "SUCCESS", "FINISHED"]


def _build_deployment_status(state: str, status: str, done_flag: str) -> DeploymentStatus:
    """Build deployment status from parsed values.

    Args:
        state: Deployment state
        status: Deployment status
        done_flag: "DONE" or "CONTINUE"

    Returns:
        DeploymentStatus object
    """
    dep_status = DeploymentStatus(state=state, status=status, done_flag=done_flag)
    dep_status.is_failure = _is_failure_status(state, status)
    dep_status.is_success = _is_success_state(state)
    return dep_status
