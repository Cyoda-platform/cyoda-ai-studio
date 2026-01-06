"""Tool for getting an entity by ID."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Getting entity {entity_id} from {cyoda_host} with client {client_id}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()
    result = await entity_service.get_by_id(entity_id, entity_model, entity_version="1")
    return format_entity_success(result)
