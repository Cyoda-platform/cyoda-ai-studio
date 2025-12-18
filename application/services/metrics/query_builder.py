"""
Prometheus Query Builder using Builder Pattern.

Provides fluent interface for constructing Prometheus queries.
"""

from typing import Dict, List, Optional


class PrometheusQueryBuilder:
    """
    Builder for Prometheus queries using fluent interface.

    Implements the Builder pattern for constructing complex Prometheus queries
    with a clean, readable syntax.

    Example:
        >>> query = (PrometheusQueryBuilder()
        ...     .metric("container_cpu_usage_seconds_total")
        ...     .for_namespace("client-myorg-dev")
        ...     .with_label("image", "", exclude_empty=True)
        ...     .rate("5m")
        ...     .sum_by(["pod"])
        ...     .build())
        >>> print(query)
        sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="client-myorg-dev",image!=""}[5m]))
    """

    def __init__(self):
        """Initialize empty query builder."""
        self._metric_name: Optional[str] = None
        self._labels: Dict[str, str] = {}
        self._label_matchers: List[str] = []
        self._aggregations: List[str] = []
        self._functions: List[str] = []
        self._range_duration: Optional[str] = None

    def metric(self, name: str) -> "PrometheusQueryBuilder":
        """
        Set the metric name.

        Args:
            name: Prometheus metric name

        Returns:
            Self for chaining

        Example:
            >>> builder.metric("container_cpu_usage_seconds_total")
        """
        self._metric_name = name
        return self

    def for_namespace(self, namespace: str) -> "PrometheusQueryBuilder":
        """
        Add namespace filter.

        Args:
            namespace: Kubernetes namespace

        Returns:
            Self for chaining

        Example:
            >>> builder.for_namespace("client-myorg-dev")
        """
        self._labels["namespace"] = namespace
        return self

    def with_label(
        self, label: str, value: str, exclude_empty: bool = False
    ) -> "PrometheusQueryBuilder":
        """
        Add label filter.

        Args:
            label: Label name
            value: Label value
            exclude_empty: If True, uses != for empty values

        Returns:
            Self for chaining

        Example:
            >>> builder.with_label("pod", "my-pod")
            >>> builder.with_label("image", "", exclude_empty=True)  # image!=""
        """
        if exclude_empty and value == "":
            self._label_matchers.append(f'{label}!=""')
        else:
            self._labels[label] = value
        return self

    def with_label_regex(self, label: str, pattern: str) -> "PrometheusQueryBuilder":
        """
        Add label regex filter.

        Args:
            label: Label name
            pattern: Regex pattern

        Returns:
            Self for chaining

        Example:
            >>> builder.with_label_regex("status", "5..")  # status=~"5.."
        """
        self._label_matchers.append(f'{label}=~"{pattern}"')
        return self

    def rate(self, duration: str = "5m") -> "PrometheusQueryBuilder":
        """
        Apply rate function.

        Args:
            duration: Time range (e.g., "5m", "1h")

        Returns:
            Self for chaining

        Example:
            >>> builder.rate("5m")  # rate(...[5m])
        """
        self._range_duration = duration
        self._functions.append("rate")
        return self

    def sum(self) -> "PrometheusQueryBuilder":
        """
        Apply sum aggregation.

        Returns:
            Self for chaining

        Example:
            >>> builder.sum()  # sum(...)
        """
        self._aggregations.append("sum")
        return self

    def sum_by(self, labels: List[str]) -> "PrometheusQueryBuilder":
        """
        Apply sum by aggregation.

        Args:
            labels: Labels to group by

        Returns:
            Self for chaining

        Example:
            >>> builder.sum_by(["pod", "namespace"])
        """
        labels_str = ", ".join(labels)
        self._aggregations.append(f"sum by ({labels_str})")
        return self

    def count(self) -> "PrometheusQueryBuilder":
        """
        Apply count aggregation.

        Returns:
            Self for chaining

        Example:
            >>> builder.count()  # count(...)
        """
        self._aggregations.append("count")
        return self

    def avg_by(self, labels: List[str]) -> "PrometheusQueryBuilder":
        """
        Apply avg by aggregation.

        Args:
            labels: Labels to group by

        Returns:
            Self for chaining

        Example:
            >>> builder.avg_by(["node"])
        """
        labels_str = ", ".join(labels)
        self._aggregations.append(f"avg by ({labels_str})")
        return self

    def histogram_quantile(self, quantile: float) -> "PrometheusQueryBuilder":
        """
        Apply histogram_quantile function.

        Args:
            quantile: Quantile to calculate (0.0-1.0)

        Returns:
            Self for chaining

        Example:
            >>> builder.histogram_quantile(0.95)  # 95th percentile
        """
        self._functions.insert(0, f"histogram_quantile({quantile}")
        return self

    def build(self) -> str:
        """
        Build final Prometheus query string.

        Returns:
            Complete Prometheus query

        Raises:
            ValueError: If metric name not set

        Example:
            >>> query = builder.build()
            >>> print(query)
        """
        if not self._metric_name:
            raise ValueError("Metric name must be set")

        # Build label selectors
        label_parts = [f'{k}="{v}"' for k, v in self._labels.items()]
        label_parts.extend(self._label_matchers)
        label_selector = ",".join(label_parts) if label_parts else ""

        # Build base metric query
        if label_selector:
            query = f"{self._metric_name}{{{label_selector}}}"
        else:
            query = self._metric_name

        # Apply range if needed
        if self._range_duration and "rate" in self._functions:
            query = f"{query}[{self._range_duration}]"

        # Apply functions (rate, etc.)
        for func in self._functions:
            if func == "rate":
                query = f"rate({query})"
            elif func.startswith("histogram_quantile"):
                # Special handling for histogram_quantile
                query = f"{func}, {query})"

        # Apply aggregations (sum, count, etc.)
        for agg in self._aggregations:
            query = f"{agg} ({query})"

        return query


class QueryTemplates:
    """
    Pre-built query templates for common metrics.

    Provides factory methods for frequently used queries.
    """

    @staticmethod
    def cpu_usage_rate(namespace: str) -> str:
        """
        CPU usage rate query.

        Args:
            namespace: Kubernetes namespace

        Returns:
            Prometheus query string
        """
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
        """
        CPU usage by pod query.

        Args:
            namespace: Kubernetes namespace

        Returns:
            Prometheus query string
        """
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
        """
        Memory usage query.

        Args:
            namespace: Kubernetes namespace

        Returns:
            Prometheus query string
        """
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
        """
        Count of pods that are up.

        Args:
            namespace: Kubernetes namespace

        Returns:
            Prometheus query string
        """
        return (
            PrometheusQueryBuilder()
            .metric("up")
            .for_namespace(namespace)
            .count()
            .build()
        )

    @staticmethod
    def http_error_rate(namespace: str) -> str:
        """
        HTTP 5xx error rate query.

        Args:
            namespace: Kubernetes namespace

        Returns:
            Prometheus query string
        """
        return (
            PrometheusQueryBuilder()
            .metric("http_requests_total")
            .for_namespace(namespace)
            .with_label_regex("status", "5..")
            .rate("5m")
            .sum()
            .build()
        )
