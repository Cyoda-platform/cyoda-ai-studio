"""Thin registry for Search subagent tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

# Search tools
from .tool_definitions.search.tools.search_entities_tool import search_entities

# Export all tools
__all__ = [
    "search_entities",
]
