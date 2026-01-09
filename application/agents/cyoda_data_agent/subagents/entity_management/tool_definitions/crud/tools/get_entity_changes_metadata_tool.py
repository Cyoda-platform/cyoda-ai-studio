"""Tool for getting entity changes metadata (audit trail)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.entity_formatters import format_entity_success
from ...common.utils.decorators import handle_entity_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_entity_errors
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
    logger.info(f"Getting changes metadata for entity {entity_id} from {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    # This would need to be implemented in the entity service
    return format_entity_success(
        {"message": "Changes metadata endpoint not yet implemented in service layer"}
    )
