"""Tool for executing a workflow transition on an entity."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Executing transition '{transition}' on {entity_model} {entity_id} in {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    entity_service = container.get_entity_service()
    result = await entity_service.execute_transition(entity_id, transition, entity_model, entity_version="1")
    return format_entity_success({"id": result.get_id(), "state": result.get_state(), "entity": result.data})
