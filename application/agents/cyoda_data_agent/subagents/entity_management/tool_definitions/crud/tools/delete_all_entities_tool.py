"""Tool for deleting all entities of a specific model type."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Deleting ALL {entity_model} entities from {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()
    count = await entity_service.delete_all(entity_model, entity_version="1")
    return format_entity_success(
        {"message": f"Deleted {count} entities of type {entity_model}"}
    )
