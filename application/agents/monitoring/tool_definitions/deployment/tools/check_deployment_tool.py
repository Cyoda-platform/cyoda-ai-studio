"""Tool for checking deployment status and making decisions."""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.monitoring_formatters import (
    format_continue_monitoring,
    format_escalate,
)

logger = logging.getLogger(__name__)


async def check_deployment_and_decide(
    tool_context: ToolContext, build_id: str
) -> str:
    """Check deployment status and decide whether to continue monitoring.

    This tool is used by the monitoring loop to check status and determine
    if monitoring should continue or stop.

    Args:
      tool_context: The ADK tool context
      build_id: The build identifier to monitor

    Returns:
      Decision message indicating whether to continue or stop monitoring
    """
    try:
        # Import the status check tool
        from application.agents.environment.tools import get_deployment_status

        # Check status with monitoring flag
        status_result = await get_deployment_status(
            tool_context, build_id, for_monitoring=True
        )

        # Parse structured response
        if status_result.startswith("STATUS:"):
            parts = status_result.replace("STATUS:", "").split("|")
            if len(parts) >= 3:
                state = parts[0]
                status = parts[1]
                decision = parts[2]

                logger.info(
                    f"Monitoring build {build_id}: state={state}, status={status}, decision={decision}"
                )

                if decision == "DONE":
                    # Deployment is complete or failed - escalate to exit loop
                    is_success = state.upper() in ["COMPLETE", "SUCCESS"]
                    return format_escalate(state, status, is_success)
                else:
                    # Still in progress - continue monitoring
                    return format_continue_monitoring(state, status)
            else:
                return format_continue_monitoring("UNKNOWN", "UNKNOWN", "Unable to parse status, will retry.")
        else:
            # Error occurred
            logger.warning(f"Status check returned error: {status_result}")
            return format_continue_monitoring("ERROR", "ERROR", status_result)

    except Exception as e:
        error_msg = f"Error checking deployment status: {str(e)}"
        logger.exception(error_msg)
        return format_continue_monitoring("ERROR", "ERROR", error_msg)
