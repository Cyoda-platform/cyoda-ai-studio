"""Tools for API Data Fetcher Subagent.

Provides functionality to fetch data from external REST APIs like Petstore Swagger.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def fetch_api_data(
    tool_context: ToolContext,
    api_url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch data from an external REST API.

    Args:
        tool_context: Google ADK tool context
        api_url: Full URL of the API endpoint
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional HTTP headers
        query_params: Optional query parameters
        body: Optional request body for POST/PUT requests

    Returns:
        API response data or error information
    """
    try:
        logger.info(f"Fetching data from {api_url} using {method}")

        async with aiohttp.ClientSession() as session:
            kwargs = {
                "headers": headers or {},
                "params": query_params or {},
            }

            if body and method.upper() in ["POST", "PUT", "PATCH"]:
                kwargs["json"] = body

            async with session.request(method.upper(), api_url, **kwargs) as response:
                data = await response.json()
                return {
                    "success": True,
                    "status_code": response.status,
                    "data": data,
                }
    except Exception as e:
        logger.exception(f"Failed to fetch API data: {e}")
        return {"success": False, "error": str(e)}


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
    try:
        logger.info(f"Searching documentation for {api_name}: {query}")
        search_query = f"{api_name} API documentation {query}"

        # Use Google Search tool from ADK
        from google.adk.tools.google_search_tool import GoogleSearchTool

        search_tool = GoogleSearchTool()
        results = await search_tool.run_async(tool_context, search_query)

        return {
            "success": True,
            "query": search_query,
            "results": results,
        }
    except Exception as e:
        logger.exception(f"Failed to search API documentation: {e}")
        return {"success": False, "error": str(e)}

