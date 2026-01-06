"""Tool for creating multiple entities in batch."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Creating {len(entities)} {entity_model} entities in {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()
    results = await entity_service.save_all(entities, entity_model, entity_version="1")
    return format_entity_success([{"id": r.get_id(), "entity": r.data} for r in results])
