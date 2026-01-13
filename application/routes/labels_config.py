"""
Labels configuration routes for AI Assistant.

Provides UI labels and text configuration for the frontend.

REFACTORED: Uses APIResponse for consistent error handling.
"""

import logging
from typing import Any, Dict

from quart import Blueprint

from application.routes.common.response import APIResponse

logger = logging.getLogger(__name__)

labels_config_bp = Blueprint("labels_config", __name__)

# Mock labels configuration for UI
# In Phase 2, this could be loaded from a config file or database
MOCK_LABELS_CONFIG: Dict[str, Any] = {
    "app": {
        "title": "AI Assistant",
        "description": "Cyoda AI Assistant powered by Google ADK",
    },
    "chat": {
        "new_chat": "New Chat",
        "delete_chat": "Delete Chat",
        "rename_chat": "Rename Chat",
        "placeholder": "Type your message...",
        "send": "Send",
        "clear": "Clear",
    },
    "canvas": {
        "title": "Canvas Questions",
        "generate": "Generate",
        "preview": "Preview",
        "apply": "Apply",
    },
    "messages": {
        "loading": "Loading...",
        "error": "An error occurred",
        "success": "Success",
        "no_chats": "No chats yet. Start a new conversation!",
        "chat_deleted": "Chat deleted successfully",
        "chat_created": "Chat created successfully",
    },
    "buttons": {
        "cancel": "Cancel",
        "confirm": "Confirm",
        "save": "Save",
        "delete": "Delete",
        "edit": "Edit",
        "close": "Close",
    },
    "forms": {
        "chat_name": "Chat Name",
        "chat_description": "Description",
        "required": "Required",
        "optional": "Optional",
    },
}


@labels_config_bp.route("", methods=["GET"])
async def get_labels_config():
    """
    Return the entire labels configuration as JSON.

    This provides UI text labels and configuration for the frontend.
    """
    try:
        return APIResponse.success(MOCK_LABELS_CONFIG)
    except Exception as e:
        logger.exception(f"Error getting labels config: {e}")
        return APIResponse.error(str(e), 500)


@labels_config_bp.route("/<path:key>", methods=["GET"])
async def get_labels_config_item(key: str):
    """
    Return a single entry from labels config.

    Key should be dot-separated, e.g.:
      /api/v1/labels_config/sidebar.links.home
    """
    try:
        # Normalize URL segment into our key format
        identifier = key.replace("-", "_")

        # Navigate through nested dict
        current: Any = MOCK_LABELS_CONFIG
        for part in identifier.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return APIResponse.error(f"Key '{key}' not found", 404)

        return APIResponse.success({key: current})
    except Exception as e:
        logger.exception(f"Error getting labels config item: {e}")
        return APIResponse.error(str(e), 500)


@labels_config_bp.route("/refresh", methods=["POST"])
async def refresh_labels_config():
    """
    Refresh labels configuration.

    In Phase 1, this is a no-op since we use mock data.
    In Phase 2, this could reload from a config file or remote service.
    """
    try:
        # Mock implementation - nothing to refresh
        return APIResponse.success(
            {
                "success": True,
                "message": "Labels configuration refreshed successfully (mock).",
            }
        )
    except Exception as e:
        logger.exception(f"Error refreshing labels config: {e}")
        return APIResponse.error(
            "Unable to refresh labels configuration at this time.",
            502,
            details={"success": False},
        )
