"""Tool for checking deployment status."""

from __future__ import annotations

import logging

import httpx
from google.adk.tools.tool_context import ToolContext

from ...common.constants.config import config
from ...common.constants.constants import STATE_UNKNOWN
from ...common.formatters.common_formatters import format_error
from ...common.formatters.deployment_formatters import format_deployment_status
from ...common.utils.decorators import handle_tool_errors

logger = logging.getLogger(__name__)


@handle_tool_errors
async def get_env_deploy_status(
    build_id: str,
    tool_context: ToolContext = None,
) -> str:
    """Check the deployment status for a given build ID.

    Makes an HTTP request to the Cyoda deployment status endpoint to check
    if the environment deployment is complete.

    Args:
        build_id: The build identifier to check status for
        tool_context: Tool context (unused but required by framework)

    Returns:
        Formatted string with deployment state and status, or error message
    """
    try:
        status_url = config.get_deploy_status_url()
    except ValueError as e:
        return format_error(str(e))

    try:
        logger.info(f"Checking deployment status for build_id: {build_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{status_url}?build_id={build_id}")
            response.raise_for_status()

            data = response.json()
            deploy_state = data.get("state", STATE_UNKNOWN)
            deploy_status = data.get("status", STATE_UNKNOWN)

            logger.info(f"Deployment status for {build_id}: {deploy_state}/{deploy_status}")
            return format_deployment_status(deploy_state, deploy_status)

    except httpx.HTTPError as e:
        error_msg = f"HTTP error checking deployment status: {str(e)}"
        logger.error(error_msg)
        return format_error(error_msg)
