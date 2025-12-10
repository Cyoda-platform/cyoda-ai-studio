"""Entity Management tools for Cyoda Data Agent subagent.

This module contains all entity-related tools including:
- Search operations (get, search, find all)
- CRUD operations (create, update, delete)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.cyoda_data_agent.user_service_container import (
    UserServiceContainer,
)
from common.service.entity_service import SearchCondition, SearchConditionRequest, SearchOperator

logger = logging.getLogger(__name__)


# ============================================================================
# SEARCH OPERATIONS
# ============================================================================


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
        logger.info(f"Getting entity {entity_id} from {cyoda_host} with client {client_id}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        result = await entity_service.get_by_id(entity_id, entity_model, entity_version="1")
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
        conditions = [
            SearchCondition(field=k, operator=SearchOperator.EQUALS, value=v)
            for k, v in search_conditions.items()
        ]
        search_request = SearchConditionRequest(conditions=conditions)

        results = await entity_service.search(entity_model, search_request, entity_version="1")
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
        logger.info(f"Finding all {entity_model} in {cyoda_host} with client {client_id}")
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


# ============================================================================
# STATISTICS OPERATIONS
# ============================================================================


async def get_entity_statistics(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    point_in_time: Optional[str] = None,
) -> dict[str, Any]:
    """Get entity statistics grouped by model name and version.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        point_in_time: Optional point-in-time in ISO 8601 format

    Returns:
        Statistics data or error information
    """
    try:
        logger.info(f"Getting entity statistics from {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        # This would need to be implemented in the entity service
        # For now, returning a placeholder
        return {"success": True, "data": {"message": "Statistics endpoint not yet implemented in service layer"}}
    except Exception as e:
        logger.exception(f"Failed to get entity statistics: {e}")
        return {"success": False, "error": str(e)}


async def get_entity_statistics_by_state(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    point_in_time: Optional[str] = None,
    states: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Get entity statistics grouped by model name, version, and state.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        point_in_time: Optional point-in-time in ISO 8601 format
        states: Optional list of states to filter by

    Returns:
        Statistics data or error information
    """
    try:
        logger.info(f"Getting entity statistics by state from {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        # This would need to be implemented in the entity service
        return {"success": True, "data": {"message": "Statistics endpoint not yet implemented in service layer"}}
    except Exception as e:
        logger.exception(f"Failed to get entity statistics by state: {e}")
        return {"success": False, "error": str(e)}


async def get_entity_statistics_for_model(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    point_in_time: Optional[str] = None,
) -> dict[str, Any]:
    """Get entity statistics for a specific model.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        point_in_time: Optional point-in-time in ISO 8601 format

    Returns:
        Statistics data or error information
    """
    try:
        logger.info(f"Getting entity statistics for {entity_model} from {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        # This would need to be implemented in the entity service
        return {"success": True, "data": {"message": "Statistics endpoint not yet implemented in service layer"}}
    except Exception as e:
        logger.exception(f"Failed to get entity statistics for model: {e}")
        return {"success": False, "error": str(e)}


async def get_entity_statistics_by_state_for_model(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    point_in_time: Optional[str] = None,
    states: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Get entity statistics by state for a specific model.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        point_in_time: Optional point-in-time in ISO 8601 format
        states: Optional list of states to filter by

    Returns:
        Statistics data or error information
    """
    try:
        logger.info(f"Getting entity statistics by state for {entity_model} from {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        # This would need to be implemented in the entity service
        return {"success": True, "data": {"message": "Statistics endpoint not yet implemented in service layer"}}
    except Exception as e:
        logger.exception(f"Failed to get entity statistics by state for model: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# CRUD OPERATIONS
# ============================================================================


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
        result = await entity_service.save(entity_data, entity_model, entity_version="1")
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
        return {"success": True, "data": {"message": f"Entity {entity_id} deleted successfully"}}
    except Exception as e:
        logger.exception(f"Failed to delete entity: {e}")
        return {"success": False, "error": str(e)}


async def get_entity_changes_metadata(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_id: str,
    point_in_time: Optional[str] = None,
) -> dict[str, Any]:
    """Get entity changes metadata (audit trail).

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_id: Entity technical UUID
        point_in_time: Optional point-in-time in ISO 8601 format

    Returns:
        Entity changes metadata or error information
    """
    try:
        logger.info(f"Getting changes metadata for entity {entity_id} from {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        # This would need to be implemented in the entity service
        return {"success": True, "data": {"message": "Changes metadata endpoint not yet implemented in service layer"}}
    except Exception as e:
        logger.exception(f"Failed to get entity changes metadata: {e}")
        return {"success": False, "error": str(e)}


async def delete_all_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
) -> dict[str, Any]:
    """Delete all entities of a specific model type (DANGEROUS - use with caution).

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type

    Returns:
        Deletion result or error information
    """
    try:
        logger.info(f"Deleting ALL {entity_model} entities from {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        count = await entity_service.delete_all(entity_model, entity_version="1")
        return {"success": True, "data": {"message": f"Deleted {count} entities of type {entity_model}"}}
    except Exception as e:
        logger.exception(f"Failed to delete all entities: {e}")
        return {"success": False, "error": str(e)}


async def create_multiple_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create multiple entities in batch.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        entities: List of entity data to create

    Returns:
        Created entities or error information
    """
    try:
        logger.info(f"Creating {len(entities)} {entity_model} entities in {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        results = await entity_service.save_all(entities, entity_model, entity_version="1")
        return {"success": True, "data": [{"id": r.get_id(), "entity": r.data} for r in results]}
    except Exception as e:
        logger.exception(f"Failed to create multiple entities: {e}")
        return {"success": False, "error": str(e)}


async def update_multiple_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update multiple entities in batch.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        entities: List of entity data to update (must include entity IDs)

    Returns:
        Updated entities or error information
    """
    try:
        logger.info(f"Updating {len(entities)} {entity_model} entities in {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        results = []
        for entity in entities:
            entity_id = entity.get("id")
            if not entity_id:
                logger.warning("Entity missing 'id' field, skipping")
                continue
            result = await entity_service.update(entity_id, entity, entity_model, entity_version="1")
            results.append({"id": result.get_id(), "entity": result.data})
        return {"success": True, "data": results}
    except Exception as e:
        logger.exception(f"Failed to update multiple entities: {e}")
        return {"success": False, "error": str(e)}


async def save_multiple_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Save multiple entities (create new or update existing) in batch.

    Automatically detects whether to create or update based on presence of 'id' field:
    - If entity has 'id' field → updates existing entity
    - If entity has no 'id' field → creates new entity

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        entities: List of entity data (with or without 'id' field)

    Returns:
        Saved entities or error information
    """
    try:
        logger.info(f"Saving {len(entities)} {entity_model} entities in {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()

        # Separate entities into create and update lists
        entities_to_create = []
        entities_to_update = []

        for entity in entities:
            if "id" in entity and entity["id"]:
                entities_to_update.append(entity)
            else:
                entities_to_create.append(entity)

        results = []

        # Create new entities
        if entities_to_create:
            logger.info(f"Creating {len(entities_to_create)} new entities")
            created = await entity_service.save_all(entities_to_create, entity_model, entity_version="1")
            results.extend([{"id": r.get_id(), "entity": r.data, "action": "created"} for r in created])

        # Update existing entities
        if entities_to_update:
            logger.info(f"Updating {len(entities_to_update)} existing entities")
            for entity in entities_to_update:
                entity_id = entity.get("id")
                result = await entity_service.update(entity_id, entity, entity_model, entity_version="1")
                results.append({"id": result.get_id(), "entity": result.data, "action": "updated"})

        return {
            "success": True,
            "data": {
                "total": len(entities),
                "created": len(entities_to_create),
                "updated": len(entities_to_update),
                "results": results
            }
        }
    except Exception as e:
        logger.exception(f"Failed to save multiple entities: {e}")
        return {"success": False, "error": str(e)}


async def execute_workflow_transition(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_model: str,
    entity_id: str,
    transition: str,
) -> dict[str, Any]:
    """Execute a workflow transition on an entity.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_model: Entity model type
        entity_id: Entity technical UUID
        transition: Transition name to execute

    Returns:
        Updated entity or error information
    """
    try:
        logger.info(f"Executing transition '{transition}' on {entity_model} {entity_id} in {cyoda_host}")
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        entity_service = container.get_entity_service()
        result = await entity_service.execute_transition(entity_id, transition, entity_model, entity_version="1")
        return {"success": True, "data": {"id": result.get_id(), "state": result.get_state(), "entity": result.data}}
    except Exception as e:
        logger.exception(f"Failed to execute workflow transition: {e}")
        return {"success": False, "error": str(e)}

