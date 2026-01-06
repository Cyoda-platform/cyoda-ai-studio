"""Helpers for creating build-related UI hooks."""

from __future__ import annotations

import logging
from typing import Optional

from application.agents.shared.hooks import (
    create_background_task_hook,
    create_combined_hook,
    create_deploy_and_open_cloud_hook,
    create_deploy_cyoda_environment_hook,
    create_launch_setup_assistant_hook,
    create_open_tasks_panel_hook,
    wrap_response_with_hook,
)

logger = logging.getLogger(__name__)


def _create_build_hooks(
    task_id: str,
    language: str,
    branch_name: str,
    repository_path: str,
    requirements: str,
    conversation_id: Optional[str],
) -> dict:
    """Create combined hooks for application build.

    Args:
        task_id: Background task ID
        language: Programming language
        branch_name: Branch name
        repository_path: Repository path
        requirements: User requirements
        conversation_id: Conversation ID

    Returns:
        Combined hooks dictionary
    """
    # Create background task hook
    background_task_hook = create_background_task_hook(
        task_id=task_id,
        task_type="application_build",
        task_name=f"Build {language} application: {branch_name}",
        task_description=f"Building complete {language} application: {requirements[:200]}...",
        conversation_id=conversation_id,
        metadata={
            "branch_name": branch_name,
            "language": language,
            "repository_path": repository_path,
        },
    )

    # Create deployment and setup hooks
    deploy_hook = create_deploy_cyoda_environment_hook(
        conversation_id=conversation_id, task_id=task_id
    )
    setup_hook = create_launch_setup_assistant_hook(
        conversation_id=conversation_id, task_id=task_id
    )
    tasks_panel_hook = create_open_tasks_panel_hook(
        conversation_id=conversation_id,
        task_id=task_id,
        message="Track build progress in the Tasks panel",
    )

    # Combine all hooks
    combined_hooks = create_combined_hook(background_task_hook=background_task_hook)
    combined_hooks["hooks"].extend([deploy_hook, setup_hook, tasks_panel_hook])

    return combined_hooks


def _create_deployment_hook(conversation_id: Optional[str]) -> dict:
    """Create deployment hook for later use.

    Args:
        conversation_id: Conversation ID

    Returns:
        Deployment hook dictionary
    """
    return create_deploy_and_open_cloud_hook(conversation_id=conversation_id)


def _format_build_response(
    task_id: str,
    branch_name: str,
    language: str,
    requirements: str,
    combined_hooks: dict,
) -> str:
    """Format build started response message.

    Args:
        task_id: Task ID
        branch_name: Branch name
        language: Programming language
        requirements: User requirements
        combined_hooks: Combined hooks

    Returns:
        Formatted response with hooks
    """
    message = f"""🚀 Application build started successfully!

📋 **Task ID:** {task_id}
🌿 **Branch:** {branch_name}
💻 **Language:** {language}
📝 **Requirements:** {requirements[:100]}{"..." if len(requirements) > 100 else ""}

⏳ The build is running in the background. This typically takes 10-30 minutes.
I'll update you when it completes. You can continue chatting while the build runs.

📊 **While you wait:**
- Click 'View Tasks' to monitor build progress
- Deploy the Cyoda environment in parallel with the build
- Launch the Setup Assistant to configure your application"""

    return wrap_response_with_hook(message, combined_hooks)
