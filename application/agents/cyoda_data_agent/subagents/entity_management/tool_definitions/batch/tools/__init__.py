"""Batch operation tools for entity management."""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation
__all__ = ["ToolContext"]

from .create_multiple_entities_tool import create_multiple_entities
from .save_multiple_entities_tool import save_multiple_entities
from .update_multiple_entities_tool import update_multiple_entities

__all__.extend(
    [
        "create_multiple_entities",
        "update_multiple_entities",
        "save_multiple_entities",
    ]
)
