"""Pre-built query templates for common metrics."""

from .builder import PrometheusQueryBuilder


class QueryTemplates:
    """Pre-built query templates for common metrics.

    Provides factory methods for frequently used queries.
    """

    @staticmethod
    def cpu_usage_rate(namespace: str) -> str:
        """CPU usage rate query."""
        return (
            PrometheusQueryBuilder()
            .metric("container_cpu_usage_seconds_total")
            .for_namespace(namespace)
            .with_label("image", "", exclude_empty=True)
            .rate("5m")
            .sum()
            .build()
        )

    @staticmethod
    def cpu_usage_by_pod(namespace: str) -> str:
        """CPU usage by pod query."""
        return (
            PrometheusQueryBuilder()
            .metric("container_cpu_usage_seconds_total")
            .for_namespace(namespace)
            .with_label("image", "", exclude_empty=True)
            .rate("5m")
            .sum_by(["pod"])
            .build()
        )

    @staticmethod
    def memory_usage(namespace: str) -> str:
        """Memory usage query."""
        return (
            PrometheusQueryBuilder()
            .metric("container_memory_usage_bytes")
            .for_namespace(namespace)
            .with_label("image", "", exclude_empty=True)
            .sum()
            .build()
        )

    @staticmethod
    def pod_status_up(namespace: str) -> str:
        """Count of pods that are up."""
        return (
            PrometheusQueryBuilder()
            .metric("up")
            .for_namespace(namespace)
            .count()
            .build()
        )

    @staticmethod
    def http_error_rate(namespace: str) -> str:
        """HTTP 5xx error rate query."""
        return (
            PrometheusQueryBuilder()
            .metric("http_requests_total")
            .for_namespace(namespace)
            .with_label_regex("status", "5..")
            .rate("5m")
            .sum()
            .build()
        )


__all__ = ["QueryTemplates"]
