"""Tool for retrieving build context (language and branch)."""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import KEY_BRANCH_NAME, KEY_LANGUAGE
from ...common.formatters.context_formatters import format_build_context
from ...common.utils.decorators import handle_tool_errors
from ..helpers._conversation_helper import get_workflow_cache

logger = logging.getLogger(__name__)


@handle_tool_errors
async def get_build_context(tool_context: ToolContext) -> str:
    """Get build context (language and branch_name) from tool_context.state or workflow_cache.

    Priority order:
    1. First check tool_context.state for language and branch_name (set by GitHub agent)
    2. If not found, retrieve from conversation's workflow_cache

    This allows the setup agent to automatically configure itself when invoked manually
    or after transfer from GitHub agent.

    Args:
        tool_context: Tool context containing session state

    Returns:
        JSON string with build context or error message
    """
    # PRIORITY 1: Check tool_context.state first (set by GitHub agent when transferring)
    language = tool_context.state.get(KEY_LANGUAGE)
    branch_name = tool_context.state.get(KEY_BRANCH_NAME)

    if language and branch_name:
        logger.info(
            f"Retrieved build context from tool_context.state: language={language}, branch={branch_name}"
        )
        return format_build_context(
            success=True,
            language=language,
            branch_name=branch_name,
            source="tool_context.state",
        )

    # PRIORITY 2: Check workflow_cache if not found in tool_context.state
    workflow_cache = await get_workflow_cache(tool_context)

    if not workflow_cache:
        return format_build_context(
            success=False,
            error="No conversation_id found in session state and no language/branch in tool_context.state",
        )

    language = workflow_cache.get(KEY_LANGUAGE)
    branch_name = workflow_cache.get(KEY_BRANCH_NAME)

    if language and branch_name:
        logger.info(
            f"Retrieved build context from workflow_cache: language={language}, branch={branch_name}"
        )
        return format_build_context(
            success=True,
            language=language,
            branch_name=branch_name,
            source="workflow_cache",
        )

    return format_build_context(
        success=False,
        error="No build context found in tool_context.state or conversation workflow_cache",
    )
