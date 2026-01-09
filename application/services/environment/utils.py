"""Utility functions for environment services."""

import re


def sanitize_namespace(name: str) -> str:
    """Sanitize name for namespace usage (lowercase, alphanumeric + hyphen)."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9-]", "-", name.lower())


def sanitize_keyspace(name: str) -> str:
    """Sanitize name for keyspace usage (lowercase, alphanumeric + underscore)."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9_]", "_", name.lower())
