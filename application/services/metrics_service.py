"""Metrics Service for Prometheus and Grafana operations.

This module provides a backward-compatible wrapper for the refactored metrics_service package.
All functionality has been split into focused modules within metrics_service/.
"""

# Re-export all public APIs from the package
from .metrics_service import (
    GrafanaOperations,
    MetricsService,
    PrometheusOperations,
    PrometheusQueryBuilder,
)

__all__ = [
    "MetricsService",
    "PrometheusQueryBuilder",
    "GrafanaOperations",
    "PrometheusOperations",
]
