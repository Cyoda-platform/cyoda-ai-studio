"""Tool for validating entity schemas."""

from __future__ import annotations

from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.canvas.models import EntitySchema
from ...common.formatters.validation_formatters import format_validation_result
from ...common.utils.decorators import handle_validation_errors


@handle_validation_errors
async def validate_entity_schema(
    entity_json: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Validate entity JSON against Cyoda schema.

    Args:
        entity_json: Entity JSON as string
        tool_context: ADK tool context

    Returns:
        Validation result with any errors
    """
    # Validate against Pydantic model
    EntitySchema.model_validate_json(entity_json)
    return format_validation_result(is_valid=True, message="Entity schema is valid")
