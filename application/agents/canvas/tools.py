"""Thin registry for Canvas agent tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

from typing import Optional

from google.adk.tools.tool_context import ToolContext

# Make ToolContext and Optional available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve these types in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext", "Optional"]

# Validation tools
from .tool_definitions.validation.tools.validate_entity_tool import validate_entity_schema
from .tool_definitions.validation.tools.validate_workflow_tool import (
    validate_workflow_schema,
)

# Hook tools
from .tool_definitions.hooks.tools.canvas_refresh_hook_tool import (
    create_canvas_refresh_hook,
)

# Export all tools
__all__.extend([
    # Validation
    "validate_workflow_schema",
    "validate_entity_schema",
    # Hooks
    "create_canvas_refresh_hook",
])
