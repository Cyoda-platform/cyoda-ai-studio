"""Deployment-related hooks for UI integration."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def create_deployment_hook(
    conversation_id: str,
    environment_name: Optional[str] = None,
    environment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook for deployment options after application build completes.

    When this hook is returned, the UI should:
    1. Show deployment options (Deploy, Redeploy, Check Status)
    2. Display warning about data cleanup on redeploy
    3. Send user's choice back to the agent

    Args:
        conversation_id: Conversation technical ID
        environment_name: Optional environment name
        environment_url: Optional environment URL

    Returns:
        Hook dictionary with type "option_selection"
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "Your application build is complete! What would you like to do?",
            "options": [
                {
                    "value": "deploy",
                    "label": "🚀 Deploy Environment",
                    "description": "Deploy your application to a new Cyoda environment"
                },
                {
                    "value": "redeploy",
                    "label": "🔄 Redeploy Environment",
                    "description": "Redeploy to existing environment (⚠️ data will be cleaned up)"
                },
                {
                    "value": "check_status",
                    "label": "📊 Check Environment Status",
                    "description": "View current environment status and details"
                }
            ],
            "selection_type": "single"
        }
    }

    if environment_name:
        hook["data"]["environment_name"] = environment_name

    if environment_url:
        hook["data"]["environment_url"] = environment_url

    logger.info(f"🎣 Created deployment_options hook for conversation {conversation_id}")
    return hook


def _create_deployment_options_hook(conversation_id: str) -> Dict[str, Any]:
    """Create deployment options hook.

    Args:
        conversation_id: Conversation technical ID

    Returns:
        Deployment options hook dictionary
    """
    return {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "Your application build is complete! What would you like to do?",
            "options": [
                {
                    "value": "deploy",
                    "label": "🚀 Deploy Environment",
                    "description": "Deploy your application to a new Cyoda environment"
                },
                {
                    "value": "redeploy",
                    "label": "🔄 Redeploy Environment",
                    "description": "Redeploy to existing environment (⚠️ data will be cleaned up)"
                },
                {
                    "value": "check_status",
                    "label": "📊 Check Environment Status",
                    "description": "View current environment status and details"
                }
            ],
            "selection_type": "single"
        }
    }


def create_deploy_and_open_cloud_hook(
    conversation_id: str,
    environment_name: Optional[str] = None,
    environment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a combined hook that opens cloud tab and shows deployment options.

    When this hook is returned, the UI should:
    1. Open the Cloud/Environments panel
    2. Show deployment options (Deploy, Redeploy, Check Status)
    3. Allow user to deploy directly from the cloud panel

    Args:
        conversation_id: Conversation technical ID
        environment_name: Optional environment name
        environment_url: Optional environment URL

    Returns:
        Hook dictionary with type "combined" containing cloud_window and deployment hooks
    """
    from .cloud_hooks import _create_cloud_window_hook

    cloud_hook = _create_cloud_window_hook(
        conversation_id, environment_name, environment_url
    )
    deployment_hook = _create_deployment_options_hook(conversation_id)

    combined = {
        "type": "combined",
        "hooks": [cloud_hook, deployment_hook]
    }

    logger.info(f"🎣 Created deploy_and_open_cloud hook for conversation {conversation_id}")
    return combined


def create_deploy_cyoda_environment_hook(
    conversation_id: str,
    task_id: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook to deploy Cyoda environment while application build is running.

    When this hook is returned, the UI should:
    1. Show "Deploy Cyoda Environment" button/option
    2. Allow user to start environment deployment in parallel with build
    3. Track deployment progress separately from build progress

    Args:
        conversation_id: Conversation technical ID
        task_id: Optional background task ID for deployment tracking
        message: Optional custom message

    Returns:
        Hook dictionary with type "option_selection" for deployment
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "While the build is running, would you like to deploy the Cyoda environment?",
            "options": [
                {
                    "value": "deploy_environment",
                    "label": "🌐 Deploy Cyoda Environment",
                    "description": "Start deploying the environment now (runs in parallel with build)"
                },
                {
                    "value": "skip_deployment",
                    "label": "⏭️ Skip for Now",
                    "description": "Deploy after the build completes"
                }
            ],
            "selection_type": "single"
        }
    }

    if task_id:
        hook["data"]["task_id"] = task_id

    if message:
        hook["data"]["message"] = message

    logger.info(f"🎣 Created deploy_cyoda_environment hook for conversation {conversation_id}")
    return hook
