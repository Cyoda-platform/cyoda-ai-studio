"""
Agent Routes for AI Assistant Application

Exposes environment agent tools as HTTP endpoints for direct access from the UI.
These routes proxy to the underlying agent tools without requiring a full conversation.
"""

import json
import logging
from datetime import timedelta
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_rate_limiter import rate_limit

from common.middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")


class SimpleToolContext:
    """Minimal tool context for calling agent tools."""
    def __init__(self, state: dict):
        self.state = state


async def _rate_limit_key() -> str:
    """Extract user ID from request for rate limiting."""
    return getattr(request, "user_id", "anonymous")


@agent_bp.route("/environment/list_environments", methods=["POST"])
@require_auth
@rate_limit(50, timedelta(minutes=1), key_function=_rate_limit_key)
async def list_environments_endpoint() -> tuple[Dict[str, Any], int]:
    """
    List all environments for the current user.
    
    Returns:
        {
            "environments": [
                {
                    "name": "dev",
                    "namespace": "client-user-dev",
                    "status": "Active",
                    "created_at": "2025-01-01T00:00:00Z"
                }
            ],
            "count": 1
        }
    """
    try:
        from application.agents.environment.tools import list_environments

        # Create a minimal tool context with user info
        tool_context = SimpleToolContext(state={
            "user_id": request.user_id,
            "conversation_id": request.headers.get("X-Conversation-ID", ""),
        })

        # Call the tool
        result_json = await list_environments(tool_context)
        result = json.loads(result_json)

        if "error" in result:
            return result, 400

        return result, 200

    except Exception as e:
        logger.exception(f"Error listing environments: {e}")
        return {"error": str(e)}, 500


@agent_bp.route("/environment/list_user_apps", methods=["POST"])
@require_auth
@rate_limit(50, timedelta(minutes=1), key_function=_rate_limit_key)
async def list_user_apps_endpoint() -> tuple[Dict[str, Any], int]:
    """
    List all user applications in a specific environment.
    
    Request body:
        {
            "env_name": "dev"
        }
    
    Returns:
        {
            "environment": "dev",
            "user_applications": [
                {
                    "app_name": "my-app",
                    "namespace": "client-1-user-dev-my-app",
                    "status": "Active",
                    "created_at": "2025-01-01T00:00:00Z"
                }
            ],
            "count": 1
        }
    """
    try:
        from application.agents.environment.tools import list_user_apps

        # Parse request
        data = await request.get_json()
        env_name = data.get("env_name")

        if not env_name:
            return {"error": "env_name parameter is required"}, 400

        # Create a minimal tool context with user info
        tool_context = SimpleToolContext(state={
            "user_id": request.user_id,
            "conversation_id": request.headers.get("X-Conversation-ID", ""),
        })

        # Call the tool
        result_json = await list_user_apps(tool_context, env_name)
        result = json.loads(result_json)

        if "error" in result:
            return result, 400

        return result, 200

    except Exception as e:
        logger.exception(f"Error listing user applications: {e}")
        return {"error": str(e)}, 500

