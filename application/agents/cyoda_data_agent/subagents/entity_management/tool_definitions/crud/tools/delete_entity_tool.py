"""Tool for deleting an entity."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Deleting {entity_model} {entity_id} from {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()
    await entity_service.delete_by_id(entity_id, entity_model, entity_version="1")
    return format_entity_success({"message": f"Entity {entity_id} deleted successfully"})
