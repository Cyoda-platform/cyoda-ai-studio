"""Thin registry for API Data Fetcher subagent tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

# API tools
from .tool_definitions.api.tools.fetch_api_data_tool import fetch_api_data
from .tool_definitions.api.tools.search_documentation_tool import (
    search_api_documentation,
)

# Export all tools
__all__ = [
    "fetch_api_data",
    "search_api_documentation",
]
