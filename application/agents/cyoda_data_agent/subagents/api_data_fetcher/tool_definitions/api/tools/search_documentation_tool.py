"""Tool for searching API documentation."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.tool_context import ToolContext

from ...common.formatters.api_formatters import format_search_success
from ...common.utils.decorators import handle_api_errors

logger = logging.getLogger(__name__)


@handle_api_errors
async def search_api_documentation(
    tool_context: ToolContext,
    api_name: str,
    query: str,
) -> dict[str, Any]:
    """Search for API documentation using Google Search.

    Args:
        tool_context: Google ADK tool context
        api_name: Name of the API (e.g., 'Petstore Swagger')
        query: Search query for the API documentation

    Returns:
        Search results with API documentation links
    """
    logger.info(f"Searching documentation for {api_name}: {query}")
    search_query = f"{api_name} API documentation {query}"

    # Use Google Search tool from ADK
    search_tool = GoogleSearchTool()
    results = await search_tool.run_async(tool_context, search_query)

    return format_search_success(search_query, results)
