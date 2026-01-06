"""Tool for exporting entity workflows."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.model_formatters import format_model_success
from ...common.utils.decorators import handle_model_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_model_errors
async def export_entity_workflows(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_name: str,
    model_version: int,
) -> dict[str, Any]:
    """Export all workflow configurations for an entity model.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_name: Entity model name
        model_version: Model version number

    Returns:
        Exported workflows or error information
    """
    logger.info(f"Exporting workflows for {entity_name} v{model_version} from {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    return format_model_success({"message": "Export workflows endpoint not yet implemented"})
