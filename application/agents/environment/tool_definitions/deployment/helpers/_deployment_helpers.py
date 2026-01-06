"""Internal deployment helper functions shared across tool implementations.

These helpers manage post-deployment tasks like background task creation,
progress monitoring, and UI hook generation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext
from services.services import get_task_service

from ...common.utils.utils import DeploymentResult, construct_environment_url
from ...common.models.dtos import DeploymentConfig
from ._tasks import (
    create_deployment_task,
    update_task_to_in_progress,
    add_task_to_conversation,
)
from ._hooks import create_deployment_hooks, store_hook_in_context
from ._deployment_monitor import monitor_deployment_progress

logger = logging.getLogger(__name__)


def _prepare_deployment_metadata(config: DeploymentConfig) -> dict[str, Any]:
    """Prepare metadata dictionary for deployment task.

    Args:
        config: Deployment configuration

    Returns:
        Metadata dictionary
    """
    metadata = {
        "build_id": config.build_id,
        "namespace": config.namespace,
        "env_url": config.env_url,
    }
    if config.additional_metadata:
        metadata.update(config.additional_metadata)
    return metadata


def _update_context_state(tool_context: ToolContext, config: DeploymentConfig, task_id: Optional[str]) -> None:
    """Update tool context state with deployment information.

    Args:
        tool_context: Tool context
        config: Deployment configuration
        task_id: Background task ID
    """
    tool_context.state.update({
        "build_id": config.build_id,
        "build_namespace": config.namespace,
        "deployment_type": config.deployment_type,
        "deployment_started": True,
        "deployment_build_id": config.build_id,
        "deployment_namespace": config.namespace,
    })
    if task_id:
        tool_context.state["deployment_task_id"] = task_id


async def _create_and_initialize_task(
    user_id: str,
    conversation_id: str,
    config: DeploymentConfig
) -> Optional[str]:
    """Create background task and initialize it.

    Args:
        user_id: User identifier.
        conversation_id: Conversation identifier.
        config: Deployment configuration.

    Returns:
        Task ID or None if creation failed.
    """
    task_id = await create_deployment_task(
        user_id=user_id,
        conversation_id=conversation_id,
        deployment_type=config.deployment_type,
        task_name=config.task_name,
        task_description=config.task_description,
        build_id=config.build_id,
        namespace=config.namespace,
        env_url=config.env_url,
    )

    if not task_id:
        return None

    # Update task status
    metadata = _prepare_deployment_metadata(config)
    await update_task_to_in_progress(task_id, config.namespace, metadata)
    await add_task_to_conversation(conversation_id, task_id)

    return task_id


def _start_deployment_monitoring(config: DeploymentConfig, task_id: str) -> None:
    """Start background monitoring for deployment.

    Args:
        config: Deployment configuration.
        task_id: Task identifier.
    """
    asyncio.create_task(
        monitor_deployment_progress(
            build_id=config.build_id,
            task_id=task_id,
            tool_context=None,  # Will be set by monitor function
        )
    )
    logger.info(f"Started monitoring for deployment {config.build_id}")


def _create_and_store_hooks(
    tool_context: ToolContext,
    conversation_id: str,
    task_id: str,
    config: DeploymentConfig,
    metadata: dict
) -> dict[str, Any]:
    """Create deployment hooks and store in context.

    Args:
        tool_context: Tool context.
        conversation_id: Conversation identifier.
        task_id: Task identifier.
        config: Deployment configuration.
        metadata: Deployment metadata.

    Returns:
        Hook dictionary.
    """
    hook = create_deployment_hooks(
        conversation_id=conversation_id,
        task_id=task_id,
        deployment_type=config.deployment_type,
        task_name=config.task_name,
        task_description=config.task_description,
        metadata=metadata,
        env_url=config.env_url,
    )
    store_hook_in_context(tool_context, hook)
    return hook


async def handle_deployment_success(
        tool_context: ToolContext,
        build_id: str,
        namespace: str,
        deployment_type: str,
        task_name: str,
        task_description: str,
        env_url: Optional[str] = None,
        additional_metadata: Optional[dict[str, Any]] = None,
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """Handle post-deployment logic: create task, hooks, start monitoring.

    Creates background task, initializes deployment monitoring, and generates
    UI hooks for user interaction. Returns early if conversation unavailable.

    Args:
        tool_context: The ADK tool context.
        build_id: The deployment build ID.
        namespace: The deployment namespace.
        deployment_type: Type of deployment.
        task_name: Name for the background task.
        task_description: Description for the background task.
        env_url: Optional environment URL.
        additional_metadata: Optional additional metadata.

    Returns:
        Tuple of (task_id, hook_dict). Both are None if conversation missing.
    """
    # Build deployment config
    config = DeploymentConfig(
        build_id=build_id,
        namespace=namespace,
        deployment_type=deployment_type,
        task_name=task_name,
        task_description=task_description,
        env_url=env_url or construct_environment_url(namespace),
        additional_metadata=additional_metadata,
    )

    # Extract context
    conversation_id = tool_context.state.get("conversation_id")
    user_id = tool_context.state.get("user_id", "guest")

    # Early return if no conversation
    if not conversation_id:
        logger.warning("No conversation_id - cannot create BackgroundTask")
        _update_context_state(tool_context, config, None)
        return None, None

    # Create task
    task_id = await _create_and_initialize_task(user_id, conversation_id, config)
    if not task_id:
        _update_context_state(tool_context, config, None)
        return None, None

    # Update context
    _update_context_state(tool_context, config, task_id)

    # Start monitoring
    _start_deployment_monitoring(config, task_id)

    # Create and store hooks
    metadata = _prepare_deployment_metadata(config)
    hook = _create_and_store_hooks(tool_context, conversation_id, task_id, config, metadata)

    return task_id, hook
