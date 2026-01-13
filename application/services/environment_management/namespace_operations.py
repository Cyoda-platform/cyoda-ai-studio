"""Namespace normalization and construction operations.

This module contains functions for:
- Namespace normalization (alphanumeric + hyphens)
- Cyoda environment namespace construction
- User application namespace construction
"""

import re


def normalize_for_namespace(name: str) -> str:
    """Normalize a name for use in Kubernetes namespace (alphanumeric + hyphens only)."""
    return re.sub(r"[^a-z0-9-]", "-", name.lower())


def construct_namespace(user_id: str, env_name: str) -> str:
    """Construct namespace for Cyoda environment.

    Args:
        user_id: User ID
        env_name: Environment name

    Returns:
        Namespace string in format: client-{user_id}-{env_name}
    """
    normalized_user = normalize_for_namespace(user_id)
    normalized_env = normalize_for_namespace(env_name)
    return f"client-{normalized_user}-{normalized_env}"


def construct_user_app_namespace(user_id: str, env_name: str, app_name: str) -> str:
    """Construct namespace for user application.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Namespace string in format: client-1-{user_id}-{env_name}-{app_name}
    """
    normalized_user = normalize_for_namespace(user_id)
    normalized_env = normalize_for_namespace(env_name)
    normalized_app = normalize_for_namespace(app_name)
    return f"client-1-{normalized_user}-{normalized_env}-{normalized_app}"
