"""Hook management utilities for environment agent tools.

This module centralizes UI hook creation logic to separate presentation
concerns from business logic.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext
from application.agents.shared.hooks import (
    create_cloud_window_hook,
    create_background_task_hook,
    create_open_tasks_panel_hook,
    create_combined_hook,
)

logger = logging.getLogger(__name__)


def _create_task_hook(
    task_id: str,
    deployment_type: str,
    task_name: str,
    task_description: str,
    conversation_id: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Create background task hook for deployment.

    Args:
        task_id: Background task ID
        deployment_type: Type of deployment
        task_name: Task name
        task_description: Task description
        conversation_id: Conversation ID
        metadata: Task metadata

    Returns:
        Background task hook dictionary
    """
    return create_background_task_hook(
        task_id=task_id,
        task_type=deployment_type,
        task_name=task_name,
        task_description=task_description,
        conversation_id=conversation_id,
        metadata=metadata,
    )


def _create_tasks_panel_hook(
    conversation_id: str,
    task_id: str,
) -> dict[str, Any]:
    """Create tasks panel hook for tracking deployment.

    Args:
        conversation_id: Conversation ID
        task_id: Task ID

    Returns:
        Tasks panel hook dictionary
    """
    return create_open_tasks_panel_hook(
        conversation_id=conversation_id,
        task_id=task_id,
        message="Track deployment progress in the Tasks panel",
    )


def _combine_hooks_with_cloud(
    cloud_hook: dict[str, Any],
    task_hook: dict[str, Any],
    tasks_panel_hook: dict[str, Any],
) -> dict[str, Any]:
    """Combine cloud window, task, and tasks panel hooks.

    Args:
        cloud_hook: Cloud window hook
        task_hook: Background task hook
        tasks_panel_hook: Tasks panel hook

    Returns:
        Combined hook dictionary
    """
    hook = create_combined_hook(
        code_changes_hook=cloud_hook,
        background_task_hook=task_hook,
    )
    hook["hooks"].append(tasks_panel_hook)
    return hook


def _combine_hooks_without_cloud(
    task_hook: dict[str, Any],
    tasks_panel_hook: dict[str, Any],
) -> dict[str, Any]:
    """Combine task and tasks panel hooks (no cloud window).

    Args:
        task_hook: Background task hook
        tasks_panel_hook: Tasks panel hook

    Returns:
        Combined hook dictionary
    """
    hook = create_combined_hook(background_task_hook=task_hook)
    hook["hooks"].append(tasks_panel_hook)
    return hook


def create_deployment_hooks(
    conversation_id: str,
    task_id: str,
    deployment_type: str,
    task_name: str,
    task_description: str,
    metadata: dict[str, Any],
    env_url: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Create combined UI hooks for deployment operations.

    Args:
        conversation_id: Conversation ID
        task_id: Background task ID
        deployment_type: Type of deployment
        task_name: Task name
        task_description: Task description
        metadata: Task metadata
        env_url: Optional environment URL

    Returns:
        Combined hook dictionary or None
    """
    if not conversation_id or not task_id:
        return None

    # Create individual hooks
    task_hook = _create_task_hook(
        task_id, deployment_type, task_name, task_description,
        conversation_id, metadata
    )
    tasks_panel_hook = _create_tasks_panel_hook(conversation_id, task_id)

    # Combine with cloud window hook if env_url provided
    if env_url:
        cloud_hook = create_cloud_window_hook(
            conversation_id=conversation_id,
            environment_url=env_url,
            environment_status="deploying",
            message="Deployment started! Track progress in the Cloud panel.",
        )
        return _combine_hooks_with_cloud(cloud_hook, task_hook, tasks_panel_hook)
    else:
        return _combine_hooks_without_cloud(task_hook, tasks_panel_hook)


def create_environment_status_hook(
        conversation_id: str,
        env_url: str,
        status: str,
        message: str,
) -> Optional[dict[str, Any]]:
    """Create cloud window hook for environment status.

    Args:
        conversation_id: Conversation ID
        env_url: Environment URL
        status: Environment status (deployed, not_deployed, unknown)
        message: Hook message

    Returns:
        Hook dictionary or None
    """
    if not conversation_id:
        return None

    return create_cloud_window_hook(
        conversation_id=conversation_id,
        environment_url=env_url,
        environment_status=status,
        message=message,
    )


def store_hook_in_context(tool_context: ToolContext, hook: Optional[dict[str, Any]]) -> None:
    """Store hook in tool context state.

    Args:
        tool_context: Tool context
        hook: Hook dictionary to store
    """
    if hook:
        tool_context.state["last_tool_hook"] = hook
