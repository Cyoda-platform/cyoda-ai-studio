"""Formatters for BackgroundTask API responses."""

import logging
from typing import Any, Dict

from .statistics import calculate_statistics

logger = logging.getLogger(__name__)


def to_api_response(task: Any) -> Dict[str, Any]:
    """Convert BackgroundTask to API response format.

    Includes calculated statistics for UI display.

    Args:
        task: BackgroundTask instance

    Returns:
        Dictionary formatted for API response
    """
    # Calculate statistics
    statistics = calculate_statistics(
        task.status,
        task.progress,
        task.error,
        task.started_at,
        task.completed_at,
    )

    return {
        "technical_id": task.technical_id,
        "user_id": task.user_id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "name": task.name,
        "description": task.description,
        "date": task.date,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "branch_name": task.branch_name,
        "language": task.language,
        "user_request": task.user_request,
        "conversation_id": task.conversation_id,
        "repository_path": task.repository_path,
        "repository_type": task.repository_type,
        "progress_messages": task.progress_messages,
        "result": task.result,
        "error": task.error,
        "error_code": task.error_code,
        "workflow_name": task.workflow_name,
        "current_state": task.current_state,
        "process_pid": task.process_pid,
        "build_job_id": task.build_job_id,
        "build_id": task.build_id,
        "namespace": task.namespace,
        "env_url": task.env_url,
        "state": task.state,
        # Statistics
        "statistics": statistics,
    }
