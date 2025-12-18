"""
Metrics Service for Prometheus and Grafana operations.

Encapsulates metrics-related business logic.
"""

import base64
import logging
from typing import Dict, Optional

import httpx

from application.routes.common.constants import (
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    SERVICE_ACCOUNT_TOKEN_EXPIRY_SECONDS,
)
from application.services.config_service import ConfigService, GrafanaConfig, PrometheusConfig

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Service for metrics operations (Grafana, Prometheus).

    Handles token generation, query building, and metrics retrieval.
    """

    def __init__(self, config_service: ConfigService):
        """
        Initialize metrics service.

        Args:
            config_service: Configuration service for external services
        """
        self.config_service = config_service

    def build_namespace(
        self, org_id: str, env_name: str, app_name: str = "cyoda"
    ) -> str:
        """
        Build Kubernetes namespace from organization, environment, and app.

        Args:
            org_id: Organization ID
            env_name: Environment name (e.g., "dev", "prod")
            app_name: Application name (default: "cyoda")

        Returns:
            Namespace string

        Example:
            >>> service = MetricsService(config)
            >>> ns = service.build_namespace("myorg", "dev", "myapp")
            >>> print(ns)  # "client-1-myorg-dev-myapp"
        """
        if app_name == "cyoda":
            return f"client-{org_id}-{env_name}"
        else:
            return f"client-1-{org_id}-{env_name}-{app_name}"

    def build_prometheus_query(
        self, query_type: str, namespace: str, **params
    ) -> str:
        """
        Build Prometheus query from query type and namespace.

        Args:
            query_type: Type of query (e.g., "cpu_usage_rate", "memory_usage")
            namespace: Kubernetes namespace
            **params: Additional parameters for the query

        Returns:
            Prometheus query string

        Raises:
            ValueError: If query_type is unknown

        Example:
            >>> query = service.build_prometheus_query(
            ...     "cpu_usage_rate",
            ...     "client-myorg-dev"
            ... )
        """
        queries = {
            "pod_status_up": f'count(up{{namespace="{namespace}"}} == 1)',
            "pod_status_down": f'count(up{{namespace="{namespace}"}} == 0)',
            "pod_count_up": f'count(up{{namespace="{namespace}"}} == 1)',
            "pod_count_down": f'count(up{{namespace="{namespace}"}} == 0)',
            "cpu_usage_rate": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
            "cpu_usage_by_pod": f'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
            "cpu_usage_by_deployment": f'sum by (deployment) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
            "cpu_usage_by_node": f'sum by (node) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
            "memory_usage": f'sum(container_memory_usage_bytes{{namespace="{namespace}", image!=""}})',
            "memory_usage_by_deployment": f'sum by (deployment) (container_memory_usage_bytes{{namespace="{namespace}", image!=""}})',
            "memory_working_set": f'sum(container_memory_working_set_bytes{{namespace="{namespace}", image!=""}})',
            "http_requests_rate": f'sum(rate(http_requests_total{{namespace="{namespace}"}}[5m]))',
            "http_errors_rate": f'sum(rate(http_requests_total{{namespace="{namespace}", status=~"5.."}}[5m]))',
            "http_request_latency_p95": f'histogram_quantile(0.95, sum by (le, handler) (rate(http_request_duration_seconds_bucket{{namespace="{namespace}"}}[5m])))',
            "pod_restarts": f'sum(kube_pod_container_status_restarts_total{{namespace="{namespace}"}})',
            "pod_not_ready": f'count(kube_pod_container_status_ready{{namespace="{namespace}"}} == 0)',
            "pod_count": f'count(kube_pod_info{{namespace="{namespace}"}})',
            "events_rate": f'sum(rate(kube_event_total{{namespace="{namespace}"}}[5m]))',
        }

        if query_type not in queries:
            available = ", ".join(queries.keys())
            raise ValueError(
                f"Unknown query type: {query_type}. Available types: {available}"
            )

        return queries[query_type]

    async def generate_grafana_token(self, org_id: str) -> Dict:
        """
        Generate Grafana service account token for organization.

        Args:
            org_id: Organization ID

        Returns:
            Dictionary with token, name, service_account_id, grafana_url, etc.

        Raises:
            Exception: If token generation fails

        Example:
            >>> result = await service.generate_grafana_token("myorg")
            >>> token = result["token"]
        """
        grafana_config = self.config_service.get_grafana_config()

        # Service account and token name
        sa_name = f"metrics-{org_id}"
        token_name = f"{sa_name}-token"

        # Create auth header
        auth_header = self._create_basic_auth_header(
            grafana_config.admin_user, grafana_config.admin_password
        )

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS, verify=False
        ) as client:
            base_url = f"https://{grafana_config.host}"

            # Check if service account exists
            sa_list_response = await client.get(
                f"{base_url}/api/serviceaccounts/search", headers=headers
            )

            if sa_list_response.status_code != 200:
                raise Exception(
                    f"Failed to list service accounts: {sa_list_response.text}"
                )

            service_accounts = sa_list_response.json()
            existing_sa = next(
                (
                    sa
                    for sa in service_accounts.get("serviceAccounts", [])
                    if sa["name"] == sa_name
                ),
                None,
            )

            if existing_sa:
                sa_id = existing_sa["id"]
                logger.info(f"Found existing service account: {sa_id}")
            else:
                # Create new service account
                sa_create_response = await client.post(
                    f"{base_url}/api/serviceaccounts",
                    headers=headers,
                    json={"name": sa_name, "role": "Viewer", "isDisabled": False},
                )

                if sa_create_response.status_code not in [200, 201]:
                    raise Exception(
                        f"Failed to create service account: {sa_create_response.text}"
                    )

                sa_data = sa_create_response.json()
                sa_id = sa_data["id"]
                logger.info(f"Created service account with ID: {sa_id}")

            # Create token
            token_response = await client.post(
                f"{base_url}/api/serviceaccounts/{sa_id}/tokens",
                headers=headers,
                json={
                    "name": token_name,
                    "secondsToLive": SERVICE_ACCOUNT_TOKEN_EXPIRY_SECONDS,
                },
            )

            if token_response.status_code not in [200, 201]:
                raise Exception(f"Failed to create token: {token_response.text}")

            token_data = token_response.json()
            token = token_data["key"]

            logger.info(f"Generated Grafana token for org: {org_id}")

            return {
                "token": token,
                "name": sa_name,
                "service_account_id": sa_id,
                "grafana_url": f"https://{grafana_config.host}",
                "namespace": f"client-{org_id}",
                "message": "Token generated. Save it securely - you won't be able to see it again.",
                "expires_in_days": 365,
            }

    async def query_prometheus(
        self,
        query: str,
        time: Optional[str] = None,
        timeout: Optional[str] = None,
    ) -> Dict:
        """
        Query Prometheus metrics.

        Args:
            query: Prometheus query string
            time: Optional evaluation timestamp
            timeout: Optional query timeout

        Returns:
            Prometheus query results

        Raises:
            Exception: If query fails

        Example:
            >>> result = await service.query_prometheus('up{namespace="client-myorg-dev"}')
        """
        prometheus_config = self.config_service.get_prometheus_config()

        params = {"query": query}
        if time:
            params["time"] = time
        if timeout:
            params["timeout"] = timeout

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS, verify=False
        ) as client:
            response = await client.post(
                f"https://{prometheus_config.host}/api/v1/query",
                headers=headers,
                data=params,
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Prometheus query failed: {response.text}")

            return response.json()

    async def query_prometheus_range(
        self,
        org_id: str,
        env_name: str,
        app_name: str,
        query_type: str,
        start: str,
        end: str,
        step: str = "15s",
    ) -> Dict:
        """
        Query Prometheus metrics over a time range.

        Args:
            org_id: Organization ID for namespace
            env_name: Environment name
            app_name: Application name
            query_type: Type of query (cpu_usage_rate, memory_usage, etc.)
            start: Start time (ISO 8601 or Unix timestamp)
            end: End time (ISO 8601 or Unix timestamp)
            step: Query resolution step interval

        Returns:
            Prometheus range query results

        Raises:
            ValueError: If query_type is invalid
            Exception: If query fails

        Example:
            >>> result = await service.query_prometheus_range(
            ...     org_id="myorg",
            ...     env_name="dev",
            ...     app_name="cyoda",
            ...     query_type="cpu_usage_rate",
            ...     start="2025-12-17T00:00:00Z",
            ...     end="2025-12-17T12:00:00Z",
            ...     step="15s"
            ... )
        """
        # Build namespace
        namespace = self.build_namespace(
            org_id=org_id, env_name=env_name, app_name=app_name
        )

        # Build query
        try:
            query = self.build_prometheus_query(query_type, namespace)
        except ValueError as e:
            raise ValueError(f"Invalid query_type: {e}")

        # Query Prometheus range endpoint
        prometheus_config = self.config_service.get_prometheus_config()

        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS, verify=False
        ) as client:
            response = await client.post(
                f"https://{prometheus_config.host}/api/v1/query_range",
                headers=headers,
                data=params,
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Prometheus range query failed: {response.text}")

            return response.json()

    async def query_prometheus_range_custom(
        self,
        org_id: str,
        query: str,
        start: str,
        end: str,
        step: str = "15s",
    ) -> Dict:
        """
        Query Prometheus with a custom query over a time range.

        Args:
            org_id: Organization ID for namespace filtering
            query: Custom Prometheus query string
            start: Start time (ISO 8601 or Unix timestamp)
            end: End time (ISO 8601 or Unix timestamp)
            step: Query resolution step interval

        Returns:
            Prometheus range query results

        Raises:
            Exception: If query fails

        Example:
            >>> result = await service.query_prometheus_range_custom(
            ...     org_id="myorg",
            ...     query='up{namespace=~"client-myorg-.*"}',
            ...     start="2025-12-17T00:00:00Z",
            ...     end="2025-12-17T12:00:00Z"
            ... )
        """
        prometheus_config = self.config_service.get_prometheus_config()

        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS, verify=False
        ) as client:
            response = await client.post(
                f"https://{prometheus_config.host}/api/v1/query_range",
                headers=headers,
                data=params,
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Prometheus range query failed: {response.text}")

            return response.json()

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
