"""Formatters for knowledge base tools."""

from __future__ import annotations

from typing import Any


def format_concepts_found(query: str, matches: dict[str, Any]) -> dict[str, Any]:
    """Format successful concept search.

    Args:
        query: Search query
        matches: Matching concepts

    Returns:
        Formatted response
    """
    return {
        "found": True,
        "query": query,
        "matches": matches,
    }


def format_concepts_not_found(query: str, suggestion: str) -> dict[str, Any]:
    """Format concept not found response.

    Args:
        query: Search query
        suggestion: Suggested alternatives

    Returns:
        Formatted response
    """
    return {
        "found": False,
        "query": query,
        "suggestion": suggestion,
    }


def format_pattern_found(pattern: str, details: dict[str, Any]) -> dict[str, Any]:
    """Format successful pattern lookup.

    Args:
        pattern: Pattern name
        details: Pattern details

    Returns:
        Formatted response
    """
    return {
        "found": True,
        "pattern": pattern,
        "details": details,
    }


def format_pattern_not_found(pattern: str, available: list[str]) -> dict[str, Any]:
    """Format pattern not found response.

    Args:
        pattern: Pattern that was searched
        available: List of available patterns

    Returns:
        Formatted response
    """
    return {
        "found": False,
        "pattern": pattern,
        "available_patterns": available,
    }
