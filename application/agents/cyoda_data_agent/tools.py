"""Tools for Cyoda Data Agent with user-provided credentials."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

from application.agents.cyoda_data_agent.user_service_container import (
    UserServiceContainer,
)
from common.search import CyodaOperator
from common.service.entity_service import SearchConditionRequest

logger = logging.getLogger(__name__)


async def get_entity(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entity_id: str,
) -> dict[str, Any]:
    """Get an entity by ID from user's Cyoda environment.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host (e.g., 'client-123.eu.cyoda.net' or full URL)
        entity_model: Entity model type
        entity_id: Entity technical UUID

    Returns:
        Entity data or error information
    """
    try:
        logger.info(
            f"Getting entity {entity_id} from {cyoda_host} with client {client_id}"
        )
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        result = await entity_service.get_by_id(
            entity_id, entity_model, entity_version="1"
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception(f"Failed to get entity: {e}")
        return {"success": False, "error": str(e)}


async def search_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    search_conditions: dict[str, Any],
) -> dict[str, Any]:
    """Search entities in user's Cyoda environment.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host (e.g., 'client-123.eu.cyoda.net' or full URL)
        entity_model: Entity model type
        search_conditions: Search conditions (field-value pairs)

    Returns:
        Search results or error information
    """
    try:
        logger.info(f"Searching {entity_model} in {cyoda_host} with client {client_id}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()

        # Convert dict conditions to SearchConditionRequest
        from common.service.entity_service import SearchCondition

        conditions = [
            SearchCondition(field=k, operator=CyodaOperator.EQUALS, value=v)
            for k, v in search_conditions.items()
        ]
        search_request = SearchConditionRequest(conditions=conditions)

        results = await entity_service.search(
            entity_model, search_request, entity_version="1"
        )
        return {"success": True, "data": results}
    except Exception as e:
        logger.exception(f"Failed to search entities: {e}")
        return {"success": False, "error": str(e)}


async def find_all_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
) -> dict[str, Any]:
    """Find all entities of a type in user's Cyoda environment.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host (e.g., 'client-123.eu.cyoda.net' or full URL)
        entity_model: Entity model type

    Returns:
        List of all entities or error information
    """
    try:
        logger.info(
            f"Finding all {entity_model} in {cyoda_host} with client {client_id}"
        )
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        results = await entity_service.find_all(entity_model, entity_version="1")
        return {"success": True, "data": results}
    except Exception as e:
        logger.exception(f"Failed to find all entities: {e}")
        return {"success": False, "error": str(e)}


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
