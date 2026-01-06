"""Tool for importing entity workflows."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.model_formatters import format_model_success
from ...common.utils.decorators import handle_model_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_model_errors
async def import_entity_workflows(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_name: str,
    model_version: int,
    workflow_data: dict[str, Any],
) -> dict[str, Any]:
    """Import or update workflow configurations for an entity model.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_name: Entity model name
        model_version: Model version number
        workflow_data: Workflow configuration data

    Returns:
        Import result or error information
    """
    logger.info(f"Importing workflows for {entity_name} v{model_version} to {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    return format_model_success({"message": "Import workflows endpoint not yet implemented"})
