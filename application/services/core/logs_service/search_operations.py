"""Log search operations for Elasticsearch."""

import logging
from typing import Dict

import httpx

from application.routes.common.constants import (
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    ELASTICSEARCH_DEFAULT_SIZE,
    ELASTICSEARCH_MAX_SIZE,
)
from application.services.core.config_service import ConfigService

from .helpers import build_log_index_pattern

logger = logging.getLogger(__name__)


def build_search_query(query: Dict, size: int, sort: list = None) -> Dict:
    """Build Elasticsearch query with validated parameters.

    Args:
        query: Elasticsearch query DSL
        size: Number of results
        sort: Sort specification (optional)

    Returns:
        Formatted search query dictionary
    """
    validated_size = min(int(size), ELASTICSEARCH_MAX_SIZE)
    return {
        "query": query,
        "size": validated_size,
        "sort": sort or [{"@timestamp": {"order": "desc"}}],
    }


async def execute_search_request(
    host: str, index_pattern: str, api_key: str, search_query: Dict
) -> httpx.Response:
    """Execute Elasticsearch search request.

    Args:
        host: Elasticsearch host
        index_pattern: Index pattern to search
        api_key: API key for authentication
        search_query: Search query body

    Returns:
        HTTP response object
    """
    async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as client:
        return await client.post(
            f"https://{host}/{index_pattern}/_search",
            headers={
                "Authorization": f"ApiKey {api_key}",
                "Content-Type": "application/json",
            },
            json=search_query,
        )


def process_search_response(response: httpx.Response) -> Dict:
    """Process Elasticsearch search response.

    Args:
        response: HTTP response from Elasticsearch

    Returns:
        Parsed search results

    Raises:
        ValueError: If API key is expired
        Exception: If search fails
    """
    if response.status_code in [200, 201]:
        result = response.json()
        hit_count = result.get("hits", {}).get("total", {}).get("value", 0)
        logger.info(f"Log search successful, found {hit_count} hits")
        return result

    logger.error(f"ELK search failed: {response.status_code} - {response.text}")

    if response.status_code == 401:
        error_text = response.text.lower()
        if "api key" in error_text and (
            "expired" in error_text or "invalid" in error_text
        ):
            raise ValueError("ELK_API_KEY_EXPIRED")

    raise Exception(f"Search failed: {response.text}")


async def search_logs(
    config_service: ConfigService,
    api_key: str,
    org_id: str,
    env_name: str,
    app_name: str,
    query: Dict,
    size: int = ELASTICSEARCH_DEFAULT_SIZE,
    sort: list = None,
) -> Dict:
    """Search logs in Elasticsearch with namespace filtering.

    Args:
        config_service: Configuration service for external services
        api_key: Elasticsearch API key
        org_id: Organization ID
        env_name: Environment name
        app_name: Application name
        query: Elasticsearch query DSL
        size: Number of results (default: 50, max: 10000)
        sort: Sort specification (optional)

    Returns:
        Elasticsearch search results

    Raises:
        Exception: If search fails

    Example:
        >>> results = await search_logs(
        ...     config,
        ...     api_key="encoded_key",
        ...     org_id="myorg",
        ...     env_name="dev",
        ...     app_name="myapp",
        ...     query={"match_all": {}},
        ...     size=100
        ... )
    """
    elk_config = config_service.get_elk_config()
    index_pattern = build_log_index_pattern(org_id, env_name, app_name)
    search_query = build_search_query(query, size, sort)

    logger.info(
        f"Searching logs for org_id={org_id}, env={env_name}, "
        f"app={app_name}, index={index_pattern}"
    )

    response = await execute_search_request(
        elk_config.host, index_pattern, api_key, search_query
    )
    return process_search_response(response)
