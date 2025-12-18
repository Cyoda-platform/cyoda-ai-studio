"""
Logs Service for Elasticsearch log management.

Encapsulates log-related business logic for API key generation and log search.
"""

import base64
import logging
import re
from typing import Dict

import httpx

from application.routes.common.constants import (
    API_KEY_EXPIRY_DAYS,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    ELASTICSEARCH_DEFAULT_SIZE,
    ELASTICSEARCH_MAX_SIZE,
)
from application.services.config_service import ConfigService, ELKConfig

logger = logging.getLogger(__name__)


class LogsService:
    """
    Service for log management operations (Elasticsearch).

    Handles API key generation and log search with namespace filtering.
    """

    def __init__(self, config_service: ConfigService):
        """
        Initialize logs service.

        Args:
            config_service: Configuration service for external services
        """
        self.config_service = config_service

    def get_namespace(self, name: str) -> str:
        """
        Transform name into valid Kubernetes namespace format.

        Converts to lowercase and replaces non-alphanumeric characters with hyphens.

        Args:
            name: Name to transform

        Returns:
            Valid namespace string

        Example:
            >>> service = LogsService(config)
            >>> ns = service.get_namespace("MyOrg123")
            >>> print(ns)  # "myorg123"
        """
        return re.sub(r"[^a-z0-9-]", "-", name.lower())

    def build_log_index_pattern(
        self, org_id: str, env_name: str, app_name: str = "cyoda"
    ) -> str:
        """
        Build Elasticsearch index pattern for logs.

        Args:
            org_id: Organization ID
            env_name: Environment name
            app_name: Application name (default: "cyoda")

        Returns:
            Elasticsearch index pattern

        Example:
            >>> pattern = service.build_log_index_pattern("myorg", "dev", "myapp")
            >>> print(pattern)  # "logs-client-1-myorg-dev-myapp*"
        """
        org_namespace = self.get_namespace(org_id)
        env_namespace = self.get_namespace(env_name)

        if app_name == "cyoda":
            return f"logs-client-{org_namespace}-{env_namespace}*"
        else:
            app_namespace = self.get_namespace(app_name)
            return f"logs-client-1-{org_namespace}-{env_namespace}-{app_namespace}*"

    async def generate_api_key(self, org_id: str) -> Dict:
        """
        Generate Elasticsearch API key for organization.

        Args:
            org_id: Organization ID

        Returns:
            Dictionary with api_key, name, created, message, expires_in_days

        Raises:
            Exception: If API key generation fails

        Example:
            >>> result = await service.generate_api_key("myorg")
            >>> api_key = result["api_key"]
        """
        elk_config = self.config_service.get_elk_config()

        # API key name
        api_key_name = f"logs-reader-{org_id}"

        # Role descriptors for read-only access
        role_descriptors = {
            f"logs_reader_{org_id}": {
                "cluster": [],
                "indices": [
                    {
                        "names": [
                            f"logs-client-{org_id}*",
                            f"logs-client-1-{org_id}*",
                        ],
                        "privileges": ["read", "view_index_metadata"],
                        "allow_restricted_indices": False,
                    }
                ],
                "run_as": [],
            }
        }

        # Create auth header
        auth_header = self._create_basic_auth_header(elk_config.user, elk_config.password)

        async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"https://{elk_config.host}/_security/api_key",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                },
                json={
                    "name": api_key_name,
                    "role_descriptors": role_descriptors,
                    "expiration": "1h",
                },
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to generate API key: {response.text}")

            result = response.json()

            # Encode API key in Elasticsearch format
            api_key_credentials = f"{result['id']}:{result['api_key']}"
            encoded_api_key = base64.b64encode(
                api_key_credentials.encode("ascii")
            ).decode("ascii")

            logger.info(f"Generated ELK API key for org: {org_id}")

            return {
                "api_key": encoded_api_key,
                "name": api_key_name,
                "created": True,
                "message": "API key generated. Save it securely - you won't be able to see it again.",
                "expires_in_days": API_KEY_EXPIRY_DAYS,
            }

    async def search_logs(
        self,
        api_key: str,
        org_id: str,
        env_name: str,
        app_name: str,
        query: Dict,
        size: int = ELASTICSEARCH_DEFAULT_SIZE,
        sort: list = None,
    ) -> Dict:
        """
        Search logs in Elasticsearch with namespace filtering.

        Args:
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
            >>> results = await service.search_logs(
            ...     api_key="encoded_key",
            ...     org_id="myorg",
            ...     env_name="dev",
            ...     app_name="myapp",
            ...     query={"match_all": {}},
            ...     size=100
            ... )
        """
        elk_config = self.config_service.get_elk_config()

        # Build index pattern
        index_pattern = self.build_log_index_pattern(org_id, env_name, app_name)

        # Validate and cap size
        size = min(int(size), ELASTICSEARCH_MAX_SIZE)

        # Build query
        search_query = {
            "query": query,
            "size": size,
            "sort": sort or [{"@timestamp": {"order": "desc"}}],
        }

        logger.info(
            f"Searching logs for org_id={org_id}, env={env_name}, "
            f"app={app_name}, index={index_pattern}"
        )

        async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"https://{elk_config.host}/{index_pattern}/_search",
                headers={
                    "Authorization": f"ApiKey {api_key}",
                    "Content-Type": "application/json",
                },
                json=search_query,
            )

            if response.status_code not in [200, 201]:
                logger.error(f"ELK search failed: {response.status_code} - {response.text}")

                # Check if API key is expired
                if response.status_code == 401:
                    error_text = response.text.lower()
                    if "api key" in error_text and ("expired" in error_text or "invalid" in error_text):
                        raise ValueError("ELK_API_KEY_EXPIRED")

                raise Exception(f"Search failed: {response.text}")

            result = response.json()
            hit_count = result.get("hits", {}).get("total", {}).get("value", 0)
            logger.info(f"Log search successful, found {hit_count} hits")

            return result

    async def check_health(self) -> Dict:
        """
        Check ELK cluster health.

        Returns:
            Dictionary with status, elk_host, cluster_status

        Example:
            >>> health = await service.check_health()
            >>> print(health["status"])  # "healthy" or "unhealthy"
        """
        try:
            elk_config = self.config_service.get_elk_config()
            auth_header = self._create_basic_auth_header(
                elk_config.user, elk_config.password
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://{elk_config.host}/_cluster/health",
                    headers={"Authorization": f"Basic {auth_header}"},
                )

                if response.status_code == 200:
                    cluster_health = response.json()
                    return {
                        "status": "healthy",
                        "elk_host": elk_config.host,
                        "cluster_status": cluster_health.get("status", "unknown"),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"ELK returned status {response.status_code}",
                    }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def _create_basic_auth_header(self, username: str, password: str) -> str:
        """
        Create Basic Authentication header value.

        Args:
            username: Username
            password: Password

        Returns:
            Base64-encoded auth string
        """
        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode("ascii")
        return base64.b64encode(auth_bytes).decode("ascii")
