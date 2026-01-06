"""Service helper functions for entity model management tools."""

from __future__ import annotations

from application.agents.cyoda_data_agent.user_service_container import (
    UserServiceContainer,
)


def get_user_service_container(
    client_id: str,
    client_secret: str,
    cyoda_host: str,
) -> UserServiceContainer:
    """Create and return a UserServiceContainer instance.

    Args:
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host (e.g., 'client-123.eu.cyoda.net' or full URL)

    Returns:
        UserServiceContainer instance
    """
    return UserServiceContainer(
        client_id=client_id,
        client_secret=client_secret,
        cyoda_host=cyoda_host,
    )
