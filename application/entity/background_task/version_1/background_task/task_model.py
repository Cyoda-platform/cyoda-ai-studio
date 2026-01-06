"""BackgroundTask entity model."""

import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class BackgroundTask(CyodaEntity):
    """BackgroundTask entity represents an asynchronous task.

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

    name: Optional[str] = Field(default="", description="Display name for the task")

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

    repository_url: Optional[str] = Field(
        default=None,
        description="GitHub repository URL for the branch",
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

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )


def add_progress_message(
    task: BackgroundTask,
    message: str,
    progress: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Add a progress update message.

    Args:
        task: BackgroundTask instance
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
        "progress": progress if progress is not None else task.progress,
        "metadata": metadata or {},
        "last_modified": timestamp_ms,
        "last_modified_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

    task.progress_messages.append(progress_entry)

    # Update current progress if provided
    if progress is not None:
        task.progress = progress


def update_status(
    task: BackgroundTask,
    status: str,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Update task status.

    Args:
        task: BackgroundTask instance
        status: New status (pending, running, completed, failed)
        message: Optional status message
        progress: Optional progress percentage
        error: Optional error message
    """
    task.status = status

    if status == "running" and not task.started_at:
        task.started_at = datetime.now(timezone.utc).isoformat()

    if status in ["completed", "failed"] and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc).isoformat()

    if error:
        task.error = error

    if message:
        add_progress_message(task, message, progress)
