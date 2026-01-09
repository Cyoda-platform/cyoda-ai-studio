"""Entity Management tools for Cyoda Data Agent subagent."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from application.agents.cyoda_data_agent.user_service_container import (
    UserServiceContainer,
)

logger = logging.getLogger(__name__)


async def create_entity(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entity_data: dict[str, Any],
) -> dict[str, Any]:
    """Create a new entity in user's Cyoda environment.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host (e.g., 'client-123.eu.cyoda.net' or full URL)
        entity_model: Entity model type
        entity_data: Entity data to create

    Returns:
        Created entity or error information
    """
    try:
        logger.info(f"Creating {entity_model} in {cyoda_host} with client {client_id}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        result = await entity_service.save(
            entity_data, entity_model, entity_version="1"
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception(f"Failed to create entity: {e}")
        return {"success": False, "error": str(e)}


async def update_entity(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entity_id: str,
    entity_data: dict[str, Any],
) -> dict[str, Any]:
    """Update an existing entity in user's Cyoda environment.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        entity_id: Entity technical UUID
        entity_data: Updated entity data

    Returns:
        Updated entity or error information
    """
    try:
        logger.info(f"Updating {entity_model} {entity_id} in {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        result = await entity_service.update(
            entity_id, entity_data, entity_model, entity_version="1"
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception(f"Failed to update entity: {e}")
        return {"success": False, "error": str(e)}


async def delete_entity(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entity_id: str,
) -> dict[str, Any]:
    """Delete an entity from user's Cyoda environment.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        entity_id: Entity technical UUID

    Returns:
        Deletion result or error information
    """
    try:
        logger.info(f"Deleting {entity_model} {entity_id} from {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        await entity_service.delete_by_id(entity_id, entity_model, entity_version="1")
        return {
            "success": True,
            "data": {"message": f"Entity {entity_id} deleted successfully"},
        }
    except Exception as e:
        logger.exception(f"Failed to delete entity: {e}")
        return {"success": False, "error": str(e)}
