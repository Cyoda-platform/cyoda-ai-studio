"""Prometheus Query Builder using Builder Pattern.

Provides fluent interface for constructing Prometheus queries.
"""

# Re-export from query_builder package for backward compatibility
from .query_builder import PrometheusQueryBuilder, QueryTemplates

__all__ = ["PrometheusQueryBuilder", "QueryTemplates"]
