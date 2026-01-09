"""Tool for exporting entity model metadata."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.model_formatters import format_model_success
from ...common.utils.decorators import handle_model_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_model_errors
async def export_model_metadata(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_name: str,
    model_version: int,
    converter: str = "JSON_SCHEMA",
) -> dict[str, Any]:
    """Export entity model metadata in specified format.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_name: Entity model name
        model_version: Model version number
        converter: Converter type (JSON_SCHEMA, SIMPLE_VIEW)

    Returns:
        Exported model metadata or error information
    """
    logger.info(f"Exporting {entity_name} v{model_version} metadata from {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    return format_model_success(
        {"message": "Export metadata endpoint not yet implemented"}
    )
