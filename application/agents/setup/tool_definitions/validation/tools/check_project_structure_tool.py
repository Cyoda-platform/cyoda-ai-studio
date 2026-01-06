"""Tool for checking project structure."""

from __future__ import annotations

from pathlib import Path

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import OPTIONAL_PROJECT_ITEMS, REQUIRED_PROJECT_ITEMS
from ...common.formatters.validation_formatters import format_project_structure_result
from ...common.utils.decorators import handle_tool_errors


@handle_tool_errors
async def check_project_structure(tool_context: ToolContext = None) -> str:
    """Check if the current directory has a valid Cyoda project structure.

    Verifies the presence of key directories and files for a Cyoda application.

    Args:
        tool_context: Tool context (unused but required by framework)

    Returns:
        JSON string with structure validation results:
          - is_valid: Overall validity
          - missing_items: List of missing required items
          - present_items: List of found items
          - recommendations: Setup recommendations
    """
    cwd = Path.cwd()
    missing = []
    present = []

    for item, item_type in REQUIRED_PROJECT_ITEMS.items():
        path = cwd / item
        if item_type == "file" and path.is_file():
            present.append(item)
        elif item_type == "directory" and path.is_dir():
            present.append(item)
        else:
            missing.append(item)

    optional_present = []
    for item, item_type in OPTIONAL_PROJECT_ITEMS.items():
        path = cwd / item
        if item_type == "file" and path.is_file():
            optional_present.append(item)
        elif item_type == "directory" and path.is_dir():
            optional_present.append(item)

    is_valid = len(missing) == 0

    recommendations = []
    if not is_valid:
        recommendations.append("Create missing required items")
        if "pyproject.toml" in missing:
            recommendations.append("Initialize Python project with pyproject.toml")
        if ".env" in missing:
            recommendations.append("Create .env file with required environment variables")
        if ".venv" in missing:
            recommendations.append("Create virtual environment: python -m venv .venv")

    return format_project_structure_result(
        is_valid=is_valid,
        missing_items=missing,
        present_items=present,
        optional_present=optional_present,
        recommendations=recommendations,
        current_directory=str(cwd),
    )
