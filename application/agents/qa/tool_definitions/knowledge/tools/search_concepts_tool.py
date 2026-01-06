"""Tool for searching Cyoda concepts."""

from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.constants.concepts import CYODA_CONCEPTS
from ...common.formatters.knowledge_formatters import (
    format_concepts_found,
    format_concepts_not_found,
)


async def search_cyoda_concepts(tool_context: ToolContext, query: str) -> dict[str, Any]:
    """Search for Cyoda concepts and terminology.

    Provides definitions and explanations for Cyoda-specific terms.

    Args:
      query: The concept or term to search for.

    Returns:
      Dictionary with concept information.
    """
    query_lower = query.lower()

    # Find matching concepts
    matches = {}
    for key, value in CYODA_CONCEPTS.items():
        if query_lower in key or key in query_lower:
            matches[key] = value

    if not matches:
        return format_concepts_not_found(
            query,
            "Try searching for: entity, workflow, processor, technical id, grpc, state"
        )

    return format_concepts_found(query, matches)
