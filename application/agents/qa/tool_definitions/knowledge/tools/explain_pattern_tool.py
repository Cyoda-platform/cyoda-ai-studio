"""Tool for explaining Cyoda patterns."""

from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.constants.patterns import CYODA_PATTERNS
from ...common.formatters.knowledge_formatters import (
    format_pattern_found,
    format_pattern_not_found,
)


async def explain_cyoda_pattern(tool_context: ToolContext, pattern: str) -> dict[str, Any]:
    """Explain Cyoda design patterns and best practices.

    Args:
      tool_context: The ADK tool context
      pattern: The pattern name to explain.

    Returns:
      Dictionary with pattern explanation and examples.
    """
    pattern_lower = pattern.lower()

    # Find matching pattern
    for key, value in CYODA_PATTERNS.items():
        if pattern_lower in key or key in pattern_lower:
            return format_pattern_found(key, value)

    return format_pattern_not_found(pattern, list(CYODA_PATTERNS.keys()))
