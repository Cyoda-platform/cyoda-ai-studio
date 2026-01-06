"""Tool for listing entity models."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.model_formatters import format_model_success
from ...common.utils.decorators import handle_model_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_model_errors
async def list_entity_models(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
) -> dict[str, Any]:
    """List all available entity models in the system.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host

    Returns:
        List of available entity models or error information
    """
    logger.info(f"Listing entity models from {cyoda_host}")
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    # This would need to be implemented in the service layer
    return format_model_success({"message": "List models endpoint not yet implemented"})
