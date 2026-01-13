"""Tool for importing entity models."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.model_formatters import format_model_success
from ...common.utils.decorators import handle_model_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_model_errors
async def import_entity_model(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_name: str,
    model_version: int,
    converter: str,
    data_format: str,
    model_data: dict[str, Any],
) -> dict[str, Any]:
    """Import or update an entity model from provided data.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_name: Entity model name
        model_version: Model version number
        converter: Converter type (SAMPLE_DATA, JSON_SCHEMA, SIMPLE_VIEW)
        data_format: Data format (JSON, XML)
        model_data: Model data to import

    Returns:
        Created/updated model UUID or error information
    """
    logger.info(f"Importing {entity_name} v{model_version} to {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    return format_model_success(
        {"message": "Import model endpoint not yet implemented"}
    )
