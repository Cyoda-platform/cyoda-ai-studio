"""Tool for validating workflow JSON against schema.

This module provides workflow validation functionality against the workflow schema.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import jsonschema

from application.agents.github.tool_definitions.common.constants import STOP_ON_ERROR

logger = logging.getLogger(__name__)


def _format_validation_error(
    error: jsonschema.ValidationError, idx: int | None = None
) -> str:
    """Format validation error message.

    Args:
        error: Validation error
        idx: Index in workflows array (None for individual workflow)

    Returns:
        Formatted error message
    """
    error_path = (
        ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
    )
    location = f"workflows[{idx}]" if idx is not None else "root"

    error_msg = f"❌ Workflow validation failed in {location}:\n"
    error_msg += f"   Location: {error_path}\n"
    error_msg += f"   Error: {error.message}\n"

    if "required" in str(error.message).lower():
        error_msg += (
            "   Hint: Check that all required fields are present in your workflow.\n"
        )
    elif "enum" in str(error.message).lower():
        error_msg += "   Hint: Check that field values match the allowed options.\n"

    error_msg += "\n   Please fix the workflow and try again."
    return error_msg


def _validate_wrapper_format(workflow: dict) -> str:
    """Validate wrapper format has required keys.

    Args:
        workflow: Workflow dictionary

    Returns:
        Empty string if valid, error message otherwise
    """
    required_keys = ["entityName", "modelVersion", "importMode", "workflows"]
    if not all(key in workflow for key in required_keys):
        return (
            "❌ Workflow validation failed: Wrapper format must include "
            "entityName, modelVersion, importMode, and workflows"
        )

    return ""


async def _validate_workflows_in_wrapper(workflows: list, schema: dict) -> str:
    """Validate each workflow in wrapper format.

    Args:
        workflows: List of workflows
        schema: JSON schema

    Returns:
        Empty string if valid, error message otherwise
    """
    for idx, wf in enumerate(workflows):
        try:
            jsonschema.validate(instance=wf, schema=schema)
        except jsonschema.ValidationError as e:
            logger.warning(f"Workflow validation failed: {e.message}")
            return _format_validation_error(e, idx)

    return ""


async def validate_workflow_against_schema(workflow_json: str) -> str:
    """Validate a workflow JSON against the workflow schema.

    This tool validates that a generated workflow matches the required schema
    before saving it to the repository. It checks:
    - Required fields (name, initialState, states)
    - State structure and transitions
    - Processor and criterion configurations
    - Execution modes and retry policies

    Supports two formats:
    1. Individual workflow: {"name": "...", "initialState": "...", "states": {...}, "version": "1" (optional)}
    2. Workflow wrapper: {"entityName": "...", "modelVersion": 1, "importMode": "...", "workflows": [...]}

    Args:
        workflow_json: The workflow JSON content as a string

    Returns:
        A validation result message with either:
        - Success message if validation passes
        - Detailed error messages if validation fails
    """
    try:
        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "prompts"
            / "workflow_schema.json"
        )
        if not schema_path.exists():
            return f"ERROR: Workflow schema not found at {schema_path}.{STOP_ON_ERROR}"

        with open(schema_path, "r") as f:
            schema_data = json.load(f)

        schema = schema_data.get("schema", schema_data)

        try:
            workflow = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            return f"❌ Workflow validation failed: Invalid JSON - {str(e)}"

        if "workflows" in workflow and isinstance(workflow.get("workflows"), list):
            error_msg = _validate_wrapper_format(workflow)
            if error_msg:
                return error_msg

            error_msg = await _validate_workflows_in_wrapper(
                workflow["workflows"], schema
            )
            if error_msg:
                return error_msg

            logger.info("✅ Workflow wrapper validation passed")
            return "✅ Workflow validation passed! The workflow wrapper matches the schema and is ready to save."

        try:
            jsonschema.validate(instance=workflow, schema=schema)
            logger.info("✅ Workflow validation passed")
            return "✅ Workflow validation passed! The workflow matches the schema and is ready to save."

        except jsonschema.ValidationError as e:
            logger.warning(f"Workflow validation failed: {e.message}")
            return _format_validation_error(e)

        except jsonschema.SchemaError as e:
            return f"ERROR: Invalid schema file - {str(e)}.{STOP_ON_ERROR}"

    except ImportError:
        return f"ERROR: jsonschema library not available. Install with: pip install jsonschema.{STOP_ON_ERROR}"
    except Exception as e:
        logger.error(f"Error validating workflow: {e}", exc_info=True)
        return f"ERROR: Failed to validate workflow: {str(e)}.{STOP_ON_ERROR}"
