"""Task management utilities for deployment operations.

This module handles background task creation and updates,
separating task management concerns from deployment logic.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.services import get_task_service

logger = logging.getLogger(__name__)


async def create_deployment_task(
        user_id: str,
        conversation_id: str,
        deployment_type: str,
        task_name: str,
        task_description: str,
        build_id: str,
        namespace: str,
        env_url: Optional[str],
) -> Optional[str]:
    """Create a background task for tracking deployment.

    Args:
        user_id: User ID
        conversation_id: Conversation ID
        deployment_type: Type of deployment
        task_name: Task name
        task_description: Task description
        build_id: Build ID
        namespace: Namespace
        env_url: Environment URL

    Returns:
        Task ID if successful, None otherwise
    """
    try:
        task_service = get_task_service()

        logger.info(
            f"Creating BackgroundTask: user_id={user_id}, "
            f"conversation_id={conversation_id}"
        )

        background_task = await task_service.create_task(
            user_id=user_id,
            task_type=deployment_type,
            name=task_name,
            description=task_description,
            conversation_id=conversation_id,
            build_id=build_id,
            namespace=namespace,
            env_url=env_url,
        )

        task_id = background_task.technical_id
        logger.info(f"Created BackgroundTask {task_id} for {deployment_type}")

        return task_id

    except Exception as e:
        logger.error(
            f"Failed to create BackgroundTask for {deployment_type}: {e}",
            exc_info=True
        )
        return None


async def update_task_to_in_progress(
        task_id: str,
        namespace: str,
        metadata: dict[str, Any],
) -> None:
    """Update task status to in_progress.

    Args:
        task_id: Task ID
        namespace: Deployment namespace
        metadata: Task metadata
    """
    try:
        task_service = get_task_service()

        await task_service.update_task_status(
            task_id=task_id,
            status="in_progress",
            message=f"Deployment started: {namespace}",
            progress=10,
            metadata=metadata,
        )

        logger.info(f"Updated BackgroundTask {task_id} to in_progress")

    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)


async def add_task_to_conversation(conversation_id: str, task_id: str) -> None:
    """Add task to conversation's background task list.

    Args:
        conversation_id: Conversation ID
        task_id: Task ID
    """
    try:
        from application.agents.shared.repository_tools import (
            _add_task_to_conversation
        )

        logger.info(f"Adding task {task_id} to conversation {conversation_id}")
        await _add_task_to_conversation(conversation_id, task_id)
        logger.info(f"Added task {task_id} to conversation {conversation_id}")

    except Exception as e:
        logger.error(
            f"Failed to add task {task_id} to conversation {conversation_id}: {e}",
            exc_info=True
        )
