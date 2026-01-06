"""Formatters for entity model management responses."""

from __future__ import annotations

from typing import Any


def format_model_success(data: Any) -> dict[str, Any]:
    """Format successful model operation response.

    Args:
        data: The data to return in the response

    Returns:
        Success response dictionary
    """
    return {"success": True, "data": data}


def format_model_error(error: str) -> dict[str, Any]:
    """Format model operation error response.

    Args:
        error: Error message

    Returns:
        Error response dictionary
    """
    return {"success": False, "error": error}
