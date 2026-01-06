"""Task and background task related hook utilities.

This module contains hook functions for:
- Background task notifications
- Task panel management
- Build and deployment task hooks
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def create_background_task_hook(
    task_id: str,
    task_type: str,
    task_name: str,
    task_description: str,
    conversation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a hook for background task launch.

    When this hook is returned, the UI should:
    1. Show task notification with description
    2. Show "View Tasks" button that opens entities window
    3. Track task progress

    Args:
        task_id: Background task technical ID
        task_type: Type of task (code_generation, application_build, etc.)
        task_name: Display name for task
        task_description: Task description
        conversation_id: Optional conversation ID
        metadata: Optional additional metadata

    Returns:
        Hook dictionary with type "background_task"
    """
    hook = {
        "type": "background_task",
        "action": "show_task_notification",
        "data": {
            "task_id": task_id,
            "task_type": task_type,
            "task_name": task_name,
            "task_description": task_description,
        }
    }

    if conversation_id:
        hook["data"]["conversation_id"] = conversation_id

    if metadata:
        hook["data"]["metadata"] = metadata

    # Also include background_task_ids for backward compatibility
    hook["background_task_ids"] = [task_id]

    logger.info(f"🎣 Created background_task hook for task {task_id}")
    return hook


def create_open_tasks_panel_hook(
    conversation_id: str,
    task_id: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook to open the Tasks panel for tracking deployment/build progress.

    When this hook is returned, the UI should:
    1. Open the Tasks panel on the right side
    2. Show task progress and status
    3. Optionally focus on a specific task if task_id is provided

    Args:
        conversation_id: Conversation technical ID
        task_id: Optional task ID to focus on
        message: Optional message to display

    Returns:
        Hook dictionary with type "tasks_panel"
    """
    hook = {
        "type": "tasks_panel",
        "action": "open_tasks_panel",
        "data": {
            "conversation_id": conversation_id,
        }
    }

    if task_id:
        hook["data"]["task_id"] = task_id

    if message:
        hook["data"]["message"] = message

    logger.info(f"🎣 Created open_tasks_panel hook for conversation {conversation_id}")
    return hook


def create_launch_setup_assistant_hook(
    conversation_id: str,
    task_id: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook to launch setup assistant for application configuration.

    When this hook is returned, the UI should:
    1. Show "Launch Setup Assistant" button/option
    2. Open interactive setup wizard for application configuration
    3. Guide user through environment variables, API keys, database setup, etc.

    Args:
        conversation_id: Conversation technical ID
        task_id: Optional background task ID for setup tracking
        message: Optional custom message

    Returns:
        Hook dictionary with type "option_selection" for setup assistant
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "Would you like to launch the Setup Assistant to configure your application?",
            "options": [
                {
                    "value": "launch_setup_assistant",
                    "label": "🛠️ Launch Setup Assistant",
                    "description": "Interactive wizard to configure environment, API keys, and services"
                },
                {
                    "value": "skip_setup_assistant",
                    "label": "⏭️ Skip Setup",
                    "description": "Configure manually later"
                }
            ],
            "selection_type": "single"
        }
    }

    if task_id:
        hook["data"]["task_id"] = task_id

    if message:
        hook["data"]["message"] = message

    logger.info(f"🎣 Created launch_setup_assistant hook for conversation {conversation_id}")
    return hook


def create_build_and_deploy_hooks(
    conversation_id: str,
    build_task_id: str,
    deploy_task_id: Optional[str] = None,
    setup_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create combined hooks for build start with deployment and setup options.

    When this hook is returned, the UI should:
    1. Show deployment environment option
    2. Show setup assistant option
    3. Allow user to start both in parallel with build

    Args:
        conversation_id: Conversation technical ID
        build_task_id: Background task ID for build
        deploy_task_id: Optional background task ID for deployment
        setup_task_id: Optional background task ID for setup

    Returns:
        Combined hook dictionary with deployment and setup options
    """
    from ..deployment_hooks import create_deploy_cyoda_environment_hook

    combined = {
        "type": "combined",
        "hooks": [
            create_deploy_cyoda_environment_hook(conversation_id, deploy_task_id),
            create_launch_setup_assistant_hook(conversation_id, setup_task_id)
        ],
        "data": {
            "build_task_id": build_task_id,
            "context": "Application build started - configure environment while build runs"
        }
    }

    logger.info(f"🎣 Created build_and_deploy_hooks for conversation {conversation_id}")
    return combined
