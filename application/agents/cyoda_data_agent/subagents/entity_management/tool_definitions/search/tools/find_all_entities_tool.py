"""Tool for finding all entities of a type."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Finding all {entity_model} in {cyoda_host} with client {client_id}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()
    results = await entity_service.find_all(entity_model, entity_version="1")
    return format_entity_success(results)
