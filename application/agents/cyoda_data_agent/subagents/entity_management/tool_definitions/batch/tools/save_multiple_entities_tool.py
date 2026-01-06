"""Tool for saving multiple entities (create new or update existing) in batch."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    - If entity has 'id' field -> updates existing entity
    - If entity has no 'id' field -> creates new entity

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
    logger.info(f"Saving {len(entities)} {entity_model} entities in {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
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

    return format_entity_success({
        "total": len(entities),
        "created": len(entities_to_create),
        "updated": len(entities_to_update),
        "results": results
    })
