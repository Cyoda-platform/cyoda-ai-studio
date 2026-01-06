"""Logs Service - Re-exports for backward compatibility."""

from .helpers import (
    get_namespace,
    build_log_index_pattern,
    build_role_descriptors,
    encode_api_key,
    create_basic_auth_header,
)
from .api_key_operations import generate_api_key, check_health
from .search_operations import (
    build_search_query,
    execute_search_request,
    process_search_response,
    search_logs,
)


class LogsService:
    """Service for log management operations (Elasticsearch).

    Handles API key generation and log search with namespace filtering.
    """

    def __init__(self, config_service):
        """Initialize logs service.

        Args:
            config_service: Configuration service for external services
        """
        self.config_service = config_service

    def get_namespace(self, name: str) -> str:
        """Transform name into valid Kubernetes namespace format."""
        return get_namespace(name)

    def build_log_index_pattern(
        self, org_id: str, env_name: str, app_name: str = "cyoda"
    ) -> str:
        """Build Elasticsearch index pattern for logs."""
        return build_log_index_pattern(org_id, env_name, app_name)

    def _build_role_descriptors(self, org_id: str):
        """Build role descriptors for read-only access."""
        return build_role_descriptors(org_id)

    def _encode_api_key(self, api_id: str, api_key: str) -> str:
        """Encode API key in Elasticsearch format."""
        return encode_api_key(api_id, api_key)

    async def generate_api_key(self, org_id: str):
        """Generate Elasticsearch API key for organization."""
        return await generate_api_key(self.config_service, org_id)

    def _build_search_query(self, query, size: int, sort=None):
        """Build Elasticsearch query with validated parameters."""
        return build_search_query(query, size, sort)

    async def _execute_search_request(self, host, index_pattern, api_key, search_query):
        """Execute Elasticsearch search request."""
        return await execute_search_request(host, index_pattern, api_key, search_query)

    def _process_search_response(self, response):
        """Process Elasticsearch search response."""
        return process_search_response(response)

    async def search_logs(
        self,
        api_key: str,
        org_id: str,
        env_name: str,
        app_name: str,
        query,
        size: int = 50,
        sort=None,
    ):
        """Search logs in Elasticsearch with namespace filtering."""
        return await search_logs(
            self.config_service,
            api_key,
            org_id,
            env_name,
            app_name,
            query,
            size,
            sort,
        )

    async def check_health(self):
        """Check ELK cluster health."""
        return await check_health(self.config_service)

    def _create_basic_auth_header(self, username: str, password: str) -> str:
        """Create Basic Authentication header value."""
        return create_basic_auth_header(username, password)


__all__ = [
    "LogsService",
    "get_namespace",
    "build_log_index_pattern",
    "build_role_descriptors",
    "encode_api_key",
    "create_basic_auth_header",
    "generate_api_key",
    "check_health",
    "build_search_query",
    "execute_search_request",
    "process_search_response",
    "search_logs",
]
