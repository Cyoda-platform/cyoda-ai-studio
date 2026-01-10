"""Statistics tools for entity management."""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation
__all__ = ["ToolContext"]

from .get_entity_statistics_by_state_for_model_tool import (
    get_entity_statistics_by_state_for_model,
)
from .get_entity_statistics_by_state_tool import get_entity_statistics_by_state
from .get_entity_statistics_for_model_tool import get_entity_statistics_for_model
from .get_entity_statistics_tool import get_entity_statistics

__all__.extend(
    [
        "get_entity_statistics",
        "get_entity_statistics_by_state",
        "get_entity_statistics_for_model",
        "get_entity_statistics_by_state_for_model",
    ]
)
