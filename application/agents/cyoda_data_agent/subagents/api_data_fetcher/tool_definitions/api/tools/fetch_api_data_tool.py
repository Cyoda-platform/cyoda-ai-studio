"""Tool for fetching data from external APIs."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from google.adk.tools.tool_context import ToolContext

from ...common.formatters.api_formatters import format_api_success
from ...common.utils.decorators import handle_api_errors

logger = logging.getLogger(__name__)


@handle_api_errors
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
            return format_api_success(response.status, data)
