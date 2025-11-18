"""
BackgroundTask Entity for AI Assistant Application

Represents an asynchronous task (like app building) stored in Cyoda.
Tracks task progress, status, and results.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class BackgroundTask(CyodaEntity):
    """
    BackgroundTask entity represents an asynchronous task.

    Stores task metadata, progress updates, and results.
    Compatible with Conversation entity structure for API consistency.
    """

    ENTITY_NAME: ClassVar[str] = "BackgroundTask"
    ENTITY_VERSION: ClassVar[int] = 1

    user_id: str = Field(..., description="User ID who owns this task")

    task_type: str = Field(
        ..., description="Type of task (e.g., 'build_app', 'deploy_env')"
    )

    status: str = Field(
        default="pending",
        description="Current status: pending, running, completed, failed",
    )

    progress: int = Field(
        default=0,
        description="Progress percentage (0-100)",
    )

    name: Optional[str] = Field(
        default="", description="Display name for the task"
    )

    description: Optional[str] = Field(
        default="", description="Optional description of the task"
    )

    date: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Creation date of the task",
    )

    started_at: Optional[str] = Field(
        default=None,
        description="When the task started execution",
    )

    completed_at: Optional[str] = Field(
        default=None,
        description="When the task completed",
    )

    # Task-specific parameters
    branch_name: Optional[str] = Field(
        default=None,
        description="Git branch name for build tasks",
    )

    language: Optional[str] = Field(
        default=None,
        description="Programming language for build tasks",
    )

    user_request: Optional[str] = Field(
        default=None,
        description="Original user request/requirements",
    )

    conversation_id: Optional[str] = Field(
        default=None,
        description="Associated conversation technical ID",
    )

    repository_path: Optional[str] = Field(
        default=None,
        description="Path to repository for build tasks",
    )

    repository_type: Optional[str] = Field(
        default=None,
        description="Repository type: public or private",
    )

    # Progress tracking
    progress_messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of progress update messages",
    )

    # Results
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task result data",
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if task failed",
    )

    error_code: Optional[str] = Field(
        default=None,
        description="Error code if task failed",
    )

    # Workflow fields
    workflow_name: Optional[str] = Field(
        default=None,
        description="Associated workflow name if any",
    )

    current_state: Optional[str] = Field(
        default=None, description="Current workflow state"
    )

    current_transition: Optional[str] = Field(
        default=None,
        description="Current workflow transition",
    )

    workflow_cache: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cache for workflow-related data",
    )

    # Process tracking
    process_pid: Optional[int] = Field(
        default=None,
        description="Process ID for running tasks",
    )

    build_job_id: Optional[str] = Field(
        default=None,
        description="Build job identifier",
    )

    # Environment deployment fields
    build_id: Optional[str] = Field(
        default=None,
        description="Cloud manager build ID for deployments",
    )

    namespace: Optional[str] = Field(
        default=None,
        description="Deployment namespace",
    )

    env_url: Optional[str] = Field(
        default=None,
        description="Environment URL for deployed applications",
    )

    def add_progress_message(
        self,
        message: str,
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a progress update message.

        Args:
            message: Progress message
            progress: Optional progress percentage (0-100)
            metadata: Optional metadata for the progress update
        """
        import time

        now = datetime.now(timezone.utc)
        timestamp_ms = int(time.time() * 1000)

        progress_entry = {
            "message": message,
            "timestamp": now.isoformat(),
            "progress": progress if progress is not None else self.progress,
            "metadata": metadata or {},
            "last_modified": timestamp_ms,
            "last_modified_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.progress_messages.append(progress_entry)

        # Update current progress if provided
        if progress is not None:
            self.progress = progress

    def update_status(
        self,
        status: str,
        message: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update task status.

        Args:
            status: New status (pending, running, completed, failed)
            message: Optional status message
            progress: Optional progress percentage
            error: Optional error message
        """
        self.status = status

        if status == "running" and not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()

        if status in ["completed", "failed"] and not self.completed_at:
            self.completed_at = datetime.now(timezone.utc).isoformat()

        if error:
            self.error = error

        if message:
            self.add_progress_message(message, progress)

    def _calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate top 3 task statistics for UI display.

        Returns:
            Dictionary with 3 key statistics
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        stats: Dict[str, Any] = {
            "duration_formatted": "0s",
            "time_remaining_formatted": None,
            "status_message": self._get_status_message(),
        }

        # 1. Duration - how long the task has been running
        if self.started_at:
            try:
                started = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
                end_time = (
                    datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
                    if self.completed_at
                    else now
                )
                duration = (end_time - started).total_seconds()
                stats["duration_formatted"] = self._format_duration(duration)

                # 2. Time remaining - estimated time until completion
                if self.status == "running" and self.progress > 0 and duration > 0:
                    progress_rate = (self.progress / duration) * 60  # % per minute
                    if progress_rate > 0:
                        remaining_progress = 100 - self.progress
                        time_remaining = (remaining_progress / progress_rate) * 60
                        stats["time_remaining_formatted"] = self._format_duration(time_remaining)

            except (ValueError, AttributeError):
                pass

        return stats

    def _get_status_message(self) -> str:
        """Get human-readable status message (statistic #3)."""
        status_messages = {
            "pending": "Waiting to start",
            "running": f"In progress - {self.progress}% complete",
            "completed": "Completed successfully",
            "failed": f"Failed: {self.error or 'Unknown error'}",
            "cancelled": "Cancelled",
        }
        return status_messages.get(self.status, f"Status: {self.status}")

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "2h 30m", "45s")
        """
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"

    def to_api_response(self) -> Dict[str, Any]:
        """
        Convert to API response format compatible with Conversation entity.
        Includes calculated statistics for UI display.

        Returns:
            Dictionary formatted for API response
        """
        # Calculate statistics
        statistics = self._calculate_statistics()

        return {
            "technical_id": self.technical_id,
            "user_id": self.user_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "name": self.name,
            "description": self.description,
            "date": self.date,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "branch_name": self.branch_name,
            "language": self.language,
            "user_request": self.user_request,
            "conversation_id": self.conversation_id,
            "repository_path": self.repository_path,
            "repository_type": self.repository_type,
            "progress_messages": self.progress_messages,
            "result": self.result,
            "error": self.error,
            "error_code": self.error_code,
            "workflow_name": self.workflow_name,
            "current_state": self.current_state,
            "process_pid": self.process_pid,
            "build_job_id": self.build_job_id,
            "build_id": self.build_id,
            "namespace": self.namespace,
            "env_url": self.env_url,
            "state": self.state,
            # Statistics
            "statistics": statistics,
        }

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

