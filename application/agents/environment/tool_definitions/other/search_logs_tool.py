"""Tool for searching application logs in Elasticsearch."""

from __future__ import annotations

import base64
import json
import logging
from typing import Optional

import httpx
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from application.services.environment_management_service import (
    get_environment_management_service,
)

from ..common.utils.utils import handle_tool_errors, require_authenticated_user

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_LOG_SIZE = 50
MAX_LOG_SIZE = 50
DEFAULT_TIME_RANGE = "15m"
ELK_REQUEST_TIMEOUT_SECONDS = 30.0
CYODA_APP_NAME = "cyoda"
INDEX_PATTERN_CYODA = "logs-client-{org_id}-{env}*"
INDEX_PATTERN_USER_APP = "logs-client-1-{org_id}-{env}-{app}*"


class ElkConfig(BaseModel):
    """Elasticsearch configuration from environment variables."""

    host: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> ElkConfig:
        """Load ELK configuration from environment variables.

        Returns:
            ElkConfig with host, user, and password.

        Raises:
            ValueError: If any required configuration is missing.
        """
        import os

        host = os.getenv("ELK_HOST", "").strip()
        user = os.getenv("ELK_USER", "").strip()
        password = os.getenv("ELK_PASSWORD", "").strip()

        if not all([host, user, password]):
            raise ValueError(
                "ELK configuration incomplete. "
                "Please configure ELK_HOST, ELK_USER, and ELK_PASSWORD."
            )
        return cls(host=host, user=user, password=password)


class LogEntry(BaseModel):
    """Structured log entry from Elasticsearch."""

    timestamp: str
    level: str
    message: str
    pod: str
    container: str
    namespace: str


class LogSearchResult(BaseModel):
    """Result of a log search operation."""

    environment: str
    app_name: str
    index_pattern: str
    total_hits: int
    returned: int
    time_range: Optional[str]
    since_timestamp: Optional[str]
    query: Optional[str]
    logs: list[LogEntry]


def _get_index_pattern(org_id: str, env: str, app_name: str, is_cyoda: bool) -> str:
    """Build Elasticsearch index pattern based on app type.

    Args:
        org_id: Normalized organization ID
        env: Normalized environment name
        app_name: Application name (ignored if is_cyoda)
        is_cyoda: Whether searching Cyoda platform logs

    Returns:
        Index pattern for Elasticsearch query
    """
    if is_cyoda:
        return INDEX_PATTERN_CYODA.format(org_id=org_id, env=env)
    return INDEX_PATTERN_USER_APP.format(org_id=org_id, env=env, app=app_name)


def _build_elasticsearch_query(
    size: int,
    query: Optional[str] = None,
    time_range: Optional[str] = None,
    since_timestamp: Optional[str] = None,
) -> dict:
    """Build Elasticsearch query with time range and search criteria.

    Args:
        size: Number of results to return
        query: Optional Lucene query string
        time_range: Relative time range (e.g., "15m", "1h")
        since_timestamp: Absolute ISO 8601 timestamp

    Returns:
        Dictionary representing the Elasticsearch query
    """
    es_query = {"size": size, "sort": [{"@timestamp": {"order": "desc"}}]}

    # Build time range filter
    if since_timestamp:
        es_query["query"] = {
            "bool": {
                "must": [],
                "filter": [
                    {"range": {"@timestamp": {"gte": since_timestamp, "lte": "now"}}}
                ],
            }
        }
    elif time_range:
        es_query["query"] = {
            "bool": {
                "must": [],
                "filter": [
                    {
                        "range": {
                            "@timestamp": {"gte": f"now-{time_range}", "lte": "now"}
                        }
                    }
                ],
            }
        }
    else:
        es_query["query"] = {"bool": {"must": []}}

    # Add search query if provided
    if query:
        es_query["query"]["bool"]["must"].append(
            {"query_string": {"query": query, "default_operator": "AND"}}
        )

    # If no query and no time range, use match_all
    if not query and not time_range:
        es_query["query"] = {"match_all": {}}

    return es_query


def _transform_log_entry(hit: dict) -> LogEntry:
    """Transform Elasticsearch hit to structured LogEntry.

    Args:
        hit: Raw Elasticsearch hit document

    Returns:
        Structured LogEntry object
    """
    source = hit.get("_source", {})
    kubernetes = source.get("kubernetes", {})

    return LogEntry(
        timestamp=source.get("@timestamp", ""),
        level=source.get("level", "INFO"),
        message=source.get("message", ""),
        pod=kubernetes.get("pod_name", "unknown"),
        container=kubernetes.get("container_name", "unknown"),
        namespace=kubernetes.get("namespace_name", "unknown"),
    )


def _create_basic_auth_header(user: str, password: str) -> str:
    """Create HTTP Basic Authentication header value.

    Args:
        user: Username
        password: Password

    Returns:
        Base64-encoded "user:password" string for Authorization header
    """
    auth_string = f"{user}:{password}"
    auth_bytes = auth_string.encode("ascii")
    return base64.b64encode(auth_bytes).decode("ascii")


@require_authenticated_user
@handle_tool_errors
async def search_logs(
    tool_context: ToolContext,
    env_name: str,
    app_name: str,
    query: Optional[str] = None,
    size: int = DEFAULT_LOG_SIZE,
    time_range: Optional[str] = DEFAULT_TIME_RANGE,
    since_timestamp: Optional[str] = None,
) -> str:
    """Search logs in Elasticsearch for a specific environment and application.

    This function searches logs for the current user's namespaces in ELK.
    It supports searching both Cyoda environment logs (app_name="cyoda") and
    user application logs.

    IMPORTANT: For newly deployed/redeployed applications, use since_timestamp
    to avoid retrieving logs from previous deployments.

    Args:
        tool_context: The ADK tool context
        env_name: Environment name (e.g., "dev", "staging", "prod")
        app_name: Application name (use "cyoda" for Cyoda platform logs)
        query: Optional search query string (Lucene syntax). If not provided, returns all logs.
        size: Number of log entries to return (default: 50, max: 1000)
        time_range: Time range for logs (default: "15m" for last 15 minutes)
                   Examples: "15m", "1h", "24h", "7d"
                   NOTE: Ignored if since_timestamp is provided
        since_timestamp: ISO 8601 timestamp (e.g., "2025-12-10T14:30:00Z")
                        Get logs ONLY after this timestamp. Use this after deployments
                        to avoid getting logs from previous deployments.

    Returns:
        JSON string with log search results, or error message

    Examples:
        - Search Cyoda platform logs: search_logs(env_name="dev", app_name="cyoda")
        - Search user app logs: search_logs(env_name="dev", app_name="my-calculator")
        - Search with query: search_logs(env_name="dev", app_name="cyoda", query="ERROR")
        - Custom time range: search_logs(env_name="dev", app_name="cyoda", time_range="1h")
        - After deployment: search_logs(env_name="prod", app_name="my-app", since_timestamp="2025-12-10T14:30:00Z")
    """
    # Validate required parameters
    if not env_name or not app_name:
        return json.dumps(
            {"error": "Both env_name and app_name parameters are required."}
        )

    # Validate and limit result size
    size = min(max(1, size), MAX_LOG_SIZE)

    # Load ELK configuration
    try:
        elk_config = ElkConfig.from_env()
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Get user ID and normalize namespace values
    user_id = tool_context.state.get("user_id", "guest")
    env_service = get_environment_management_service()
    org_id = env_service._normalize_for_namespace(user_id)
    normalized_env = env_service._normalize_for_namespace(env_name)

    # Determine index pattern based on app type
    is_cyoda = app_name.lower() == CYODA_APP_NAME
    if not is_cyoda:
        normalized_app = env_service._normalize_for_namespace(app_name)
    else:
        normalized_app = ""

    index_pattern = _get_index_pattern(org_id, normalized_env, normalized_app, is_cyoda)

    # Build Elasticsearch query
    es_query = _build_elasticsearch_query(size, query, time_range, since_timestamp)

    # Prepare HTTP request
    auth_header = _create_basic_auth_header(elk_config.user, elk_config.password)
    search_url = f"https://{elk_config.host}/{index_pattern}/_search"

    logger.info(
        f"Searching logs for user={user_id}, env={env_name}, "
        f"app={app_name}, index={index_pattern}"
    )

    # Execute search and transform results
    async with httpx.AsyncClient(timeout=ELK_REQUEST_TIMEOUT_SECONDS) as client:
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
        }
        response = await client.post(search_url, headers=headers, json=es_query)
        response.raise_for_status()

        es_result = response.json()
        hits = es_result.get("hits", {})
        total_hits = hits.get("total", {}).get("value", 0)

        # Transform raw hits to structured LogEntry objects
        logs = [_transform_log_entry(hit) for hit in hits.get("hits", [])]

        # Build result summary
        result = LogSearchResult(
            environment=env_name,
            app_name=app_name,
            index_pattern=index_pattern,
            total_hits=total_hits,
            returned=len(logs),
            time_range=time_range if not since_timestamp else None,
            since_timestamp=since_timestamp,
            query=query,
            logs=logs,
        )

        logger.info(
            f"Found {total_hits} log entries for {env_name}/{app_name}, "
            f"returning {len(logs)}"
        )
        return result.model_dump_json()
