"""Metrics Service for Prometheus and Grafana operations."""

import logging
from typing import Dict, Optional

import httpx

from application.routes.common.constants import DEFAULT_HTTP_TIMEOUT_SECONDS
from application.services.core.config_service import ConfigService

from .grafana_ops import GrafanaOperations
from .prometheus_ops import PrometheusOperations
from .query_builder import PrometheusQueryBuilder

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for metrics operations (Grafana, Prometheus).

    Handles token generation, query building, and metrics retrieval.
    """

    def __init__(self, config_service: ConfigService):
        """Initialize metrics service.

        Args:
            config_service: Configuration service for external services
        """
        self.config_service = config_service
        self.query_builder = PrometheusQueryBuilder()
        self.grafana_ops = GrafanaOperations()
        self.prometheus_ops = PrometheusOperations()

    def build_namespace(
        self, org_id: str, env_name: str, app_name: str = "cyoda"
    ) -> str:
        """Build Kubernetes namespace from organization, environment, and app."""
        return self.query_builder.build_namespace(org_id, env_name, app_name)

    def build_prometheus_query(self, query_type: str, namespace: str, **params) -> str:
        """Build Prometheus query from query type and namespace."""
        return self.query_builder.build_query(query_type, namespace, **params)

    async def generate_grafana_token(self, org_id: str) -> Dict:
        """Generate Grafana service account token for organization.

        Creates or reuses service account and generates token with expiry.

        Args:
            org_id: Organization ID.

        Returns:
            Dictionary with token, name, service_account_id, grafana_url, etc.

        Raises:
            Exception: If token generation fails.
        """
        grafana_config = self.config_service.get_grafana_config()

        # Build names
        sa_name = f"metrics-{org_id}"
        token_name = f"{sa_name}-token"

        # Create auth header
        auth_header = self.grafana_ops.create_basic_auth_header(
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

            # Find or create service account
            sa_id = await self.grafana_ops.find_or_create_service_account(
                client, base_url, headers, sa_name
            )

            # Create token
            token = await self.grafana_ops.create_service_account_token(
                client, base_url, headers, sa_id, token_name
            )

            logger.info(f"Generated Grafana token for org: {org_id}")

            return self.grafana_ops.format_token_response(
                token, sa_name, sa_id, grafana_config.host, org_id
            )

    async def query_prometheus(
        self,
        query: str,
        time: Optional[str] = None,
        timeout: Optional[str] = None,
    ) -> Dict:
        """Query Prometheus metrics.

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
        return await self.prometheus_ops.query(
            prometheus_config.host, query, time, timeout
        )

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
        """Query Prometheus metrics over a time range.

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
        return await self.prometheus_ops.query_range(
            prometheus_config.host, query, start, end, step
        )

    async def query_prometheus_range_custom(
        self,
        org_id: str,
        query: str,
        start: str,
        end: str,
        step: str = "15s",
    ) -> Dict:
        """Query Prometheus with a custom query over a time range.

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
        return await self.prometheus_ops.query_range(
            prometheus_config.host, query, start, end, step
        )
