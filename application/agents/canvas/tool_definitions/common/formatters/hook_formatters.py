"""Formatters for hook tools."""

from __future__ import annotations


def format_hook_success(message: str) -> str:
    """Format hook creation success message.

    Args:
        message: Success message

    Returns:
        Success message string
    """
    return message


def format_hook_error(error: str) -> str:
    """Format hook creation error message.

    Args:
        error: Error message

    Returns:
        Formatted error string
    """
    return f"ERROR: {error}"
