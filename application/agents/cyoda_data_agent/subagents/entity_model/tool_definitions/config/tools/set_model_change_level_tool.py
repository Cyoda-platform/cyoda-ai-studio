"""Tool for setting model change levels."""

from __future__ import annotations

import logging
from typing import Any

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.model_formatters import format_model_success
from ...common.utils.decorators import handle_model_errors
from ...common.utils.service_helpers import get_user_service_container

logger = logging.getLogger(__name__)


@handle_model_errors
async def set_model_change_level(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_name: str,
    model_version: int,
    change_level: str,
) -> dict[str, Any]:
    """Set change level for an entity model.

    Change levels (from least to most impactful):
    - ARRAY_LENGTH: Only allows UniTypeArray width increases
    - ARRAY_ELEMENTS: Permits MultiTypeArray changes without new types
    - TYPE: Allows type modifications
    - STRUCTURAL: Permits fundamental model changes

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_name: Entity model name
        model_version: Model version number
        change_level: Change level (ARRAY_LENGTH, ARRAY_ELEMENTS, TYPE, STRUCTURAL)

    Returns:
        Change level result or error information
    """
    logger.info(
        f"Setting change level {change_level} for {entity_name} v{model_version}"
    )
    container = get_user_service_container(client_id, client_secret, cyoda_host)
    return format_model_success(
        {"message": "Set change level endpoint not yet implemented"}
    )
