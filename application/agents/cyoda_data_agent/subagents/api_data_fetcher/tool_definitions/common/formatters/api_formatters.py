"""Formatters for API tools."""

from __future__ import annotations

from typing import Any


def format_api_success(status_code: int, data: Any) -> dict[str, Any]:
    """Format successful API response.

    Args:
        status_code: HTTP status code
        data: Response data

    Returns:
        Formatted success response
    """
    return {
        "success": True,
        "status_code": status_code,
        "data": data,
    }


def format_api_error(error: str) -> dict[str, Any]:
    """Format API error response.

    Args:
        error: Error message

    Returns:
        Formatted error response
    """
    return {"success": False, "error": error}


def format_search_success(query: str, results: Any) -> dict[str, Any]:
    """Format successful search response.

    Args:
        query: Search query
        results: Search results

    Returns:
        Formatted success response
    """
    return {
        "success": True,
        "query": query,
        "results": results,
    }
