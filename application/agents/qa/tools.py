"""Tools for the QA agent."""

from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext


async def search_cyoda_concepts(tool_context: ToolContext, query: str) -> dict[str, Any]:
    """Search for Cyoda concepts and terminology.

    Provides definitions and explanations for Cyoda-specific terms.

    Args:
      query: The concept or term to search for.

    Returns:
      Dictionary with concept information.
    """
    # Knowledge base of Cyoda concepts
    concepts = {
        "technical id": {
            "definition": "Unique UUID identifier for entities in Cyoda",
            "usage": "Prefer technical IDs over business IDs for entity operations",
            "example": 'entity_service.get_by_id(entity_id="uuid-here")',
        },
        "entity": {
            "definition": "Core data object in Cyoda with lifecycle and state management",
            "components": ["technical ID", "business data", "state", "workflow"],
            "operations": ["create", "read", "update", "delete", "transition"],
        },
        "workflow": {
            "definition": "State machine defining entity lifecycle and transitions",
            "components": ["states", "transitions", "processors"],
            "types": ["manual transitions", "automatic transitions"],
        },
        "processor": {
            "definition": "Event handler for entity state changes",
            "types": ["calc", "criteria", "ack", "error", "keep_alive"],
            "execution": "Triggered by gRPC events from Cyoda",
        },
        "grpc": {
            "definition": "Communication protocol between Cyoda client and server",
            "usage": "Event-driven processing via gRPC streams",
            "events": ["calc", "criteria", "ack", "error"],
        },
        "state": {
            "definition": "Current lifecycle stage of an entity",
            "management": "Workflow-managed and read-only",
            "transitions": "Changed via manual transitions only",
        },
    }

    query_lower = query.lower()

    # Find matching concepts
    matches = {}
    for key, value in concepts.items():
        if query_lower in key or key in query_lower:
            matches[key] = value

    if not matches:
        return {
            "found": False,
            "query": query,
            "suggestion": "Try searching for: entity, workflow, processor, technical id, grpc, state",
        }

    return {
        "found": True,
        "query": query,
        "matches": matches,
    }


async def explain_cyoda_pattern(tool_context: ToolContext, pattern: str) -> dict[str, Any]:
    """Explain Cyoda design patterns and best practices.

    Args:
      tool_context: The ADK tool context
      pattern: The pattern name to explain.

    Returns:
      Dictionary with pattern explanation and examples.
    """
    patterns = {
        "no reflection": {
            "principle": "Avoid dynamic imports and reflection",
            "reason": "Improves code clarity and IDE support",
            "instead": "Use common module patterns and explicit imports",
            "example": "from common.entity import CyodaEntity",
        },
        "thin routes": {
            "principle": "Routes are proxies to EntityService",
            "reason": "Separation of concerns, testability",
            "pattern": "Route -> EntityService -> Cyoda",
            "example": "await entity_service.create(entity_data)",
        },
        "manual transitions": {
            "principle": "Use manual transitions for entity updates",
            "reason": "Explicit state management, workflow control",
            "usage": 'entity_service.update(..., transition="approve")',
            "avoid": "Automatic transitions for business logic",
        },
        "technical ids": {
            "principle": "Prefer technical IDs over business IDs",
            "reason": "Guaranteed uniqueness, performance",
            "usage": "entity_service.get_by_id(entity_id=uuid)",
            "avoid": "Searching by business fields when ID is known",
        },
        "workflow-managed state": {
            "principle": "Entity state is read-only",
            "reason": "Workflow controls lifecycle",
            "management": "State changes via transitions only",
            "avoid": "Direct state field modification",
        },
    }

    pattern_lower = pattern.lower()

    # Find matching pattern
    for key, value in patterns.items():
        if pattern_lower in key or key in pattern_lower:
            return {
                "found": True,
                "pattern": key,
                "details": value,
            }

    return {
        "found": False,
        "pattern": pattern,
        "available_patterns": list(patterns.keys()),
    }
