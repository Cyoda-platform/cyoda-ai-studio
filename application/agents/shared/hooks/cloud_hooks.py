"""Cloud/environment-related hooks for UI integration."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def create_cloud_window_hook(
    conversation_id: str,
    environment_url: Optional[str] = None,
    environment_status: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook for opening the Cloud/Environments window in the UI.

    When this hook is returned, the UI should:
    1. Open the Cloud/Environments panel (left sidebar)
    2. Highlight the user's environment if it exists
    3. Show environment status and details

    Args:
        conversation_id: Conversation technical ID
        environment_url: Optional environment URL (e.g., "https://client-user.cyoda.cloud")
        environment_status: Optional environment status (e.g., "deployed", "pending", "failed")
        message: Optional message to display to user

    Returns:
        Hook dictionary with type "cloud_window"
    """
    hook = {
        "type": "cloud_window",
        "action": "open_environments_panel",
        "data": {
            "conversation_id": conversation_id,
        }
    }

    if environment_url:
        hook["data"]["environment_url"] = environment_url

    if environment_status:
        hook["data"]["environment_status"] = environment_status

    if message:
        hook["data"]["message"] = message
    else:
        hook["data"]["message"] = "View your Cyoda environment details in the Cloud panel."

    logger.info(f"🎣 Created cloud_window hook for conversation {conversation_id}")
    return hook


def _create_cloud_window_hook(
    conversation_id: str,
    environment_name: Optional[str] = None,
    environment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create cloud window hook to open deployment panel.

    Args:
        conversation_id: Conversation technical ID
        environment_name: Optional environment name
        environment_url: Optional environment URL

    Returns:
        Cloud window hook dictionary
    """
    hook = {
        "type": "cloud_window",
        "action": "open_environments_panel",
        "data": {
            "conversation_id": conversation_id,
            "message": "🚀 Build complete! Deploy your application to a Cyoda environment.",
        }
    }

    if environment_url:
        hook["data"]["environment_url"] = environment_url

    if environment_name:
        hook["data"]["environment_name"] = environment_name

    return hook
