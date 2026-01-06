"""Tool for waiting before next deployment check."""

from __future__ import annotations

import asyncio
import logging

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.monitoring_formatters import format_wait_confirmation

logger = logging.getLogger(__name__)


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
    return format_wait_confirmation(seconds)
