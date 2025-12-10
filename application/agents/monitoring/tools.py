"""Tools for the Deployment Monitoring agent."""

from __future__ import annotations

import asyncio
import logging

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

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
                    if state.upper() in ["COMPLETE", "SUCCESS"]:
                        return f"ESCALATE:Deployment completed successfully! State: {state}, Status: {status}"
                    else:
                        return f"ESCALATE:Deployment failed. State: {state}, Status: {status}"
                else:
                    # Still in progress - continue monitoring
                    return f"CONTINUE:Deployment in progress. State: {state}, Status: {status}. Will check again in 30 seconds."
            else:
                return "CONTINUE:Unable to parse status, will retry."
        else:
            # Error occurred
            logger.warning(f"Status check returned error: {status_result}")
            return f"CONTINUE:{status_result}"

    except Exception as e:
        error_msg = f"Error checking deployment status: {str(e)}"
        logger.exception(error_msg)
        return f"CONTINUE:{error_msg}"


async def wait_before_next_check(tool_context: ToolContext, seconds: int = 30) -> str:
    """Wait for a specified number of seconds before the next status check.

    Args:
      tool_context: The ADK tool context
      seconds: Number of seconds to wait (default: 30)

    Returns:
      Confirmation message
    """
    logger.info(f"Waiting {seconds} seconds before next deployment status check")
    await asyncio.sleep(seconds)
    return f"Waited {seconds} seconds. Ready for next status check."

