"""Common formatters used across all tools."""

from __future__ import annotations

import json


def format_error(error_message: str) -> str:
    """Format error message.

    Args:
        error_message: Error message

    Returns:
        JSON string with error
    """
    return json.dumps({"error": error_message})


def format_success_message(message: str) -> str:
    """Format success message.

    Args:
        message: Success message

    Returns:
        Success message string
    """
    return message
