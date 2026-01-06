"""Formatters for validation tools."""

from __future__ import annotations

import json


def format_validation_result(is_valid: bool, message: str | None = None, errors: list[str] | None = None) -> str:
    """Format validation result.

    Args:
        is_valid: Whether validation passed
        message: Success message
        errors: List of validation errors

    Returns:
        JSON string with validation result
    """
    result = {"valid": is_valid}

    if is_valid and message:
        result["message"] = message
    elif not is_valid and errors:
        result["errors"] = errors

    return json.dumps(result)
