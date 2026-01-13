"""Prometheus Query Builder using Builder Pattern."""

from typing import Dict, List, Optional


class PrometheusQueryBuilder:
    """Builder for Prometheus queries using fluent interface.

    Implements the Builder pattern for constructing complex Prometheus queries
    with a clean, readable syntax.
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
        """Set the metric name."""
        self._metric_name = name
        return self

    def for_namespace(self, namespace: str) -> "PrometheusQueryBuilder":
        """Add namespace filter."""
        self._labels["namespace"] = namespace
        return self

    def with_label(
        self, label: str, value: str, exclude_empty: bool = False
    ) -> "PrometheusQueryBuilder":
        """Add label filter."""
        if exclude_empty and value == "":
            self._label_matchers.append(f'{label}!=""')
        else:
            self._labels[label] = value
        return self

    def with_label_regex(self, label: str, pattern: str) -> "PrometheusQueryBuilder":
        """Add label regex filter."""
        self._label_matchers.append(f'{label}=~"{pattern}"')
        return self

    def rate(self, duration: str = "5m") -> "PrometheusQueryBuilder":
        """Apply rate function."""
        self._range_duration = duration
        self._functions.append("rate")
        return self

    def sum(self) -> "PrometheusQueryBuilder":
        """Apply sum aggregation."""
        self._aggregations.append("sum")
        return self

    def sum_by(self, labels: List[str]) -> "PrometheusQueryBuilder":
        """Apply sum by aggregation."""
        labels_str = ", ".join(labels)
        self._aggregations.append(f"sum by ({labels_str})")
        return self

    def count(self) -> "PrometheusQueryBuilder":
        """Apply count aggregation."""
        self._aggregations.append("count")
        return self

    def avg_by(self, labels: List[str]) -> "PrometheusQueryBuilder":
        """Apply avg by aggregation."""
        labels_str = ", ".join(labels)
        self._aggregations.append(f"avg by ({labels_str})")
        return self

    def histogram_quantile(self, quantile: float) -> "PrometheusQueryBuilder":
        """Apply histogram_quantile function."""
        self._functions.insert(0, f"histogram_quantile({quantile}")
        return self

    def build(self) -> str:
        """Build final Prometheus query string."""
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


__all__ = ["PrometheusQueryBuilder"]
