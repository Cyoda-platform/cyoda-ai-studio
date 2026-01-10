"""Thin registry for API Data Fetcher subagent tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

# API tools
from .tool_definitions.api.tools.fetch_api_data_tool import fetch_api_data
from .tool_definitions.api.tools.search_documentation_tool import (
    search_api_documentation,
)

# Export all tools
__all__.extend(
    [
        "fetch_api_data",
        "search_api_documentation",
    ]
)
