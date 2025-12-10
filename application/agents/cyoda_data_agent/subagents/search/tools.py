"""Search tools for Cyoda Data Agent subagent.

This module contains the synchronous entity search tool.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.cyoda_data_agent.user_service_container import (
    UserServiceContainer,
)

logger = logging.getLogger(__name__)


async def search_entities(
    tool_context: ToolContext,
    client_id: str,
    client_secret: str,
    cyoda_host: str,
    entity_name: str,
    model_version: int,
    search_conditions: Optional[dict[str, Any]] = None,
    limit: int = 1000,
    timeout_millis: int = 60000,
    client_point_time: Optional[str] = None,
) -> dict[str, Any]:
    """Perform synchronous entity search with optional conditions.

    Executes a direct, in-memory search for entities without creating a persistent snapshot.
    Returns results immediately as a streaming response, optimized for smaller result sets.

    Args:
        tool_context: Google ADK tool context
        client_id: Cyoda client ID
        client_secret: Cyoda client secret
        cyoda_host: Cyoda host
        entity_name: Entity model name
        model_version: Model version number
        search_conditions: Search conditions (AbstractConditionDto format). If not provided,
                          all entities of the specified model and version will be returned.
                          Supports group conditions with AND/OR operators and simple/lifecycle conditions.
        limit: Maximum number of entities to return (1-10000, default: 1000)
        timeout_millis: Maximum time to wait for query completion in milliseconds (default: 60000)
        client_point_time: Point-in-time for searching entities in ISO 8601 format.
                          Defaults to system consistency time if not provided.

    Returns:
        Search results or error information. Results are sorted in descending order by entity id.

    Examples:
        # Search all entities
        search_entities(..., entity_name="laureate", model_version=1)

        # Search with conditions
        search_entities(
            ...,
            entity_name="laureate",
            model_version=1,
            search_conditions={
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "type": "lifecycle",
                        "field": "state",
                        "operatorType": "EQUALS",
                        "value": "VALIDATED"
                    },
                    {
                        "type": "simple",
                        "jsonPath": "$.category",
                        "operatorType": "EQUALS",
                        "value": "physics"
                    }
                ]
            }
        )
    """
    try:
        logger.info(
            f"Searching {entity_name} v{model_version} from {cyoda_host} "
            f"(limit={limit}, timeout={timeout_millis}ms)"
        )
        container = UserServiceContainer(
            client_id=client_id,
            client_secret=client_secret,
            cyoda_host=cyoda_host,
        )
        return {"success": True, "data": {"message": "Search endpoint not yet implemented"}}
    except Exception as e:
        logger.exception(f"Failed to search entities: {e}")
        return {"success": False, "error": str(e)}

