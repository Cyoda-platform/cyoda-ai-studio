"""Tool for searching entities."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from common.search import CyodaOperator
from common.service.entity_service import SearchCondition, SearchConditionRequest

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Searching {entity_model} in {cyoda_host} with client {client_id}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()

    # Convert dict conditions to SearchConditionRequest
    conditions = [
        SearchCondition(field=k, operator=CyodaOperator.EQUALS, value=v)
        for k, v in search_conditions.items()
    ]
    search_request = SearchConditionRequest(conditions=conditions)

    results = await entity_service.search(
        entity_model, search_request, entity_version="1"
    )
    return format_entity_success(results)
