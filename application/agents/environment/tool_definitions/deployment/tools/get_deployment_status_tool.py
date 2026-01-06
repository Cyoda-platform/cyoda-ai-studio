"""Tool for checking deployment status."""

from __future__ import annotations

import httpx
import logging
import os

from google.adk.tools.tool_context import ToolContext

from application.services.cloud_manager_service import get_cloud_manager_service

logger = logging.getLogger(__name__)


def _resolve_status_path() -> str:
    """Resolve deployment status path from environment or use default.

    Returns:
        Status endpoint path.
    """
    status_path = os.getenv("DEPLOY_CYODA_ENV_STATUS")
    if status_path:
        if "://" in status_path:
            return "/" + status_path.split("://", 1)[1].split("/", 1)[1]
        return status_path
    return "/deploy/cyoda-env/status"


def _is_deployment_complete(state: str, status: str) -> bool:
    """Check if deployment is complete.

    Args:
        state: Deployment state.
        status: Deployment status.

    Returns:
        True if deployment is complete or failed.
    """
    is_complete = state.upper() in ["COMPLETE", "SUCCESS", "FINISHED"] and status.upper() != "UNKNOWN"
    is_failed = state.upper() in ["FAILED", "ERROR", "UNKNOWN"] or status.upper() == "UNKNOWN"
    return is_complete or is_failed


def _build_monitoring_response(state: str, status: str) -> str:
    """Build response for monitoring loop.

    Args:
        state: Deployment state.
        status: Deployment status.

    Returns:
        Monitoring response string.
    """
    is_complete = _is_deployment_complete(state, status)
    return f"STATUS:{state}|{status}|{'DONE' if is_complete else 'CONTINUE'}"


def _get_status_emoji(state: str) -> str:
    """Get emoji for deployment state.

    Args:
        state: Deployment state.

    Returns:
        Emoji character.
    """
    emoji_map = {
        "PENDING": "⏳",
        "RUNNING": "🔄",
        "COMPLETE": "✅",
        "SUCCESS": "✅",
        "FINISHED": "✅",
        "FAILED": "❌",
        "ERROR": "❌",
        "UNKNOWN": "❌",
    }
    return emoji_map.get(state.upper(), "📊")


def _build_status_message(state: str, status: str, message: str, build_id: str) -> str:
    """Build formatted status message.

    Args:
        state: Deployment state.
        status: Deployment status.
        message: Status message from service.
        build_id: Build identifier.

    Returns:
        Formatted status message.
    """
    status_emoji = _get_status_emoji(state)
    result = f"""{status_emoji} **Deployment Status for Build {build_id}**

**State:** {state}
**Status:** {status}"""

    if message:
        result += f"\n**Message:** {message}"

    # Add helpful next steps
    if status.upper() == "UNKNOWN":
        result += "\n\n⚠️ Deployment failed: status is UNKNOWN. You can check the build logs for more details."
    elif state.upper() in ["COMPLETE", "SUCCESS", "FINISHED"]:
        result += "\n\n✓ Deployment completed successfully! Your environment is ready to use."
    elif state.upper() in ["FAILED", "ERROR", "UNKNOWN"]:
        result += "\n\n⚠️ Deployment failed. You can check the build logs for more details."
    elif state.upper() in ["PENDING", "RUNNING"]:
        result += "\n\n⏳ Deployment is still in progress. I'll keep monitoring for you."

    return result


async def get_deployment_status(
        tool_context: ToolContext, build_id: str, for_monitoring: bool = False
) -> str:
    """Check the deployment status for a specific build.

    Queries the cloud manager to get current state and status. Returns
    structured data for monitoring loops or formatted message for display.

    Args:
      tool_context: The ADK tool context
      build_id: The build identifier to check status for
      for_monitoring: If True, returns structured data for monitoring loop

    Returns:
      Formatted deployment status information, or error message
    """
    try:
        # Resolve status path
        status_path = _resolve_status_path()
        logger.info(f"Checking deployment status for build_id: {build_id}")

        # Get client and make request
        client = await get_cloud_manager_service()
        response = await client.get(f"{status_path}?build_id={build_id}")
        data = response.json()
        state = data.get("state", "UNKNOWN")
        status = data.get("status", "UNKNOWN")
        message = data.get("message", "")

        # Store status in session state (if context is available)
        if tool_context:
            tool_context.state[f"deployment_status_{build_id}"] = {
                "state": state,
                "status": status,
                "message": message,
            }

        # Return monitoring response if requested
        if for_monitoring:
            return _build_monitoring_response(state, status)

        # Build formatted status message
        result = _build_status_message(state, status, message, build_id)
        logger.info(f"Deployment status for {build_id}: {state}/{status}")
        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: Build ID '{build_id}' not found. Please verify the build ID and try again."
        error_msg = f"Status request failed with status {e.response.status_code}"
        logger.error(f"{error_msg}: {e.response.text}")
        return f"Error: {error_msg}"
    except httpx.HTTPError as e:
        error_msg = f"Network error checking deployment status: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error checking deployment status: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}"
