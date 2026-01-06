"""Query building utilities for Prometheus."""

import logging

logger = logging.getLogger(__name__)


class PrometheusQueryBuilder:
    """Builds Prometheus queries for various metrics."""

    @staticmethod
    def build_namespace(org_id: str, env_name: str, app_name: str = "cyoda") -> str:
        """Build Kubernetes namespace from organization, environment, and app.

        Args:
            org_id: Organization ID
            env_name: Environment name (e.g., "dev", "prod")
            app_name: Application name (default: "cyoda")

        Returns:
            Namespace string

        Example:
            >>> ns = PrometheusQueryBuilder.build_namespace("myorg", "dev", "myapp")
            >>> print(ns)  # "client-1-myorg-dev-myapp"
        """
        if app_name == "cyoda":
            return f"client-{org_id}-{env_name}"
        else:
            return f"client-1-{org_id}-{env_name}-{app_name}"

    @staticmethod
    def build_query(query_type: str, namespace: str, **params) -> str:
        """Build Prometheus query from query type and namespace.

        Args:
            query_type: Type of query (e.g., "cpu_usage_rate", "memory_usage")
            namespace: Kubernetes namespace
            **params: Additional parameters for the query

        Returns:
            Prometheus query string

        Raises:
            ValueError: If query_type is unknown

        Example:
            >>> query = PrometheusQueryBuilder.build_query(
            ...     "cpu_usage_rate",
            ...     "client-myorg-dev"
            ... )
        """
        queries = {
            "pod_status_up": f'count(up{{namespace="{namespace}"}} == 1)',
            "pod_status_down": f'count(up{{namespace="{namespace}"}} == 0)',
            "pod_count_up": f'count(up{{namespace="{namespace}"}} == 1)',
            "pod_count_down": f'count(up{{namespace="{namespace}"}} == 0)',
            "cpu_usage_rate": (
                f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))'
            ),
            "cpu_usage_by_pod": (
                f'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))'
            ),
            "cpu_usage_by_deployment": (
                f'sum by (deployment) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", '
                f'image!=""}}[5m]))'
            ),
            "cpu_usage_by_node": (
                f'sum by (node) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))'
            ),
            "memory_usage": f'sum(container_memory_usage_bytes{{namespace="{namespace}", image!=""}})',
            "memory_usage_by_deployment": (
                f'sum by (deployment) (container_memory_usage_bytes{{namespace="{namespace}", image!=""}})'
            ),
            "memory_working_set": f'sum(container_memory_working_set_bytes{{namespace="{namespace}", image!=""}})',
            "http_requests_rate": f'sum(rate(http_requests_total{{namespace="{namespace}"}}[5m]))',
            "http_errors_rate": f'sum(rate(http_requests_total{{namespace="{namespace}", status=~"5.."}}[5m]))',
            "http_request_latency_p95": (
                f'histogram_quantile(0.95, sum by (le, handler) '
                f'(rate(http_request_duration_seconds_bucket{{namespace="{namespace}"}}[5m])))'
            ),
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
