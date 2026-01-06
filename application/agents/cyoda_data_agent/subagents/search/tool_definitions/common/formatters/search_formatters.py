"""Formatters for search tools."""

from __future__ import annotations

from typing import Any


def format_search_success(data: Any) -> dict[str, Any]:
    """Format successful search response.

    Args:
        data: Search results

    Returns:
        Formatted success response
    """
    return {"success": True, "data": data}


def format_search_error(error: str) -> dict[str, Any]:
    """Format search error response.

    Args:
        error: Error message

    Returns:
        Formatted error response
    """
    return {"success": False, "error": error}
