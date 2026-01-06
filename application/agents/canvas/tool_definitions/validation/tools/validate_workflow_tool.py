"""Tool for validating workflow schemas."""

from __future__ import annotations

from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.canvas.models import WorkflowSchema
from ...common.formatters.validation_formatters import format_validation_result
from ...common.utils.decorators import handle_validation_errors


@handle_validation_errors
async def validate_workflow_schema(
    workflow_json: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Validate workflow JSON against Cyoda schema.

    Args:
        workflow_json: Workflow JSON as string
        tool_context: ADK tool context

    Returns:
        Validation result with any errors
    """
    # Validate against Pydantic model
    WorkflowSchema.model_validate_json(workflow_json)
    return format_validation_result(is_valid=True, message="Workflow schema is valid")
