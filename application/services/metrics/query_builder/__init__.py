"""Prometheus Query Builder using Builder Pattern.

Provides fluent interface for constructing Prometheus queries.

Internal organization:
- builder.py: PrometheusQueryBuilder class
- templates.py: Pre-built query templates
"""

from .builder import PrometheusQueryBuilder
from .templates import QueryTemplates

__all__ = ["PrometheusQueryBuilder", "QueryTemplates"]
