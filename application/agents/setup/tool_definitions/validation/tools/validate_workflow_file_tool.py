"""Tool for validating workflow files."""

from __future__ import annotations

import json
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import REQUIRED_WORKFLOW_FIELDS
from ...common.formatters.validation_formatters import format_workflow_validation_result
from ...common.utils.decorators import handle_tool_errors


@handle_tool_errors
async def validate_workflow_file(
    file_path: str,
    tool_context: ToolContext = None,
) -> str:
    """Validate a Cyoda workflow JSON file.

    Checks if the workflow file exists and has valid JSON structure.

    Args:
        file_path: Path to the workflow JSON file (relative or absolute)
        tool_context: Tool context (unused but required by framework)

    Returns:
        JSON string with validation results:
          - is_valid: Whether the file is valid
          - exists: Whether the file exists
          - error: Error message if invalid
          - file_path: Resolved file path
    """
    path = Path(file_path)

    if not path.exists():
        return format_workflow_validation_result(
            is_valid=False,
            exists=False,
            error=f"File not found: {file_path}",
            file_path=str(path.absolute()),
        )

    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Basic validation - check for required workflow fields
        missing_fields = [f for f in REQUIRED_WORKFLOW_FIELDS if f not in data]

        if missing_fields:
            return format_workflow_validation_result(
                is_valid=False,
                exists=True,
                error=f'Missing required fields: {", ".join(missing_fields)}',
                file_path=str(path.absolute()),
            )

        return format_workflow_validation_result(
            is_valid=True,
            exists=True,
            error=None,
            file_path=str(path.absolute()),
            workflow_name=data.get("name"),
            num_states=len(data.get("states", [])),
            num_transitions=len(data.get("transitions", [])),
        )

    except json.JSONDecodeError as e:
        return format_workflow_validation_result(
            is_valid=False,
            exists=True,
            error=f"Invalid JSON: {str(e)}",
            file_path=str(path.absolute()),
        )
