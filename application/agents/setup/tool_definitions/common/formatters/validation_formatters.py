"""Formatters for validation tools."""

from __future__ import annotations

import json


def format_validation_result(result: dict[str, bool]) -> str:
    """Format environment validation result.

    Args:
        result: Dictionary mapping variable names to their presence status

    Returns:
        Formatted string representation
    """
    return json.dumps(result, indent=2)


def format_project_structure_result(
    is_valid: bool,
    missing_items: list[str],
    present_items: list[str],
    optional_present: list[str],
    recommendations: list[str],
    current_directory: str,
) -> str:
    """Format project structure check result.

    Args:
        is_valid: Whether the project structure is valid
        missing_items: List of missing required items
        present_items: List of present required items
        optional_present: List of present optional items
        recommendations: List of recommendations
        current_directory: Current working directory

    Returns:
        JSON string with formatted result
    """
    return json.dumps(
        {
            "is_valid": is_valid,
            "missing_items": missing_items,
            "present_items": present_items,
            "optional_present": optional_present,
            "recommendations": recommendations,
            "current_directory": current_directory,
        },
        indent=2,
    )


def format_workflow_validation_result(
    is_valid: bool,
    exists: bool,
    error: str | None,
    file_path: str,
    **extra_fields,
) -> str:
    """Format workflow validation result.

    Args:
        is_valid: Whether the workflow file is valid
        exists: Whether the file exists
        error: Error message if any
        file_path: Path to the workflow file
        **extra_fields: Additional fields to include

    Returns:
        JSON string with formatted result
    """
    result = {
        "is_valid": is_valid,
        "exists": exists,
        "error": error,
        "file_path": file_path,
    }
    result.update(extra_fields)
    return json.dumps(result, indent=2)
