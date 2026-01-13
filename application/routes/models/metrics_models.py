"""
Request/Response models for metrics routes.

Provides type-safe models for Prometheus and Grafana operations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Valid Prometheus query types
VALID_QUERY_TYPES = [
    "pod_status_up",
    "pod_status_down",
    "pod_count_up",
    "pod_count_down",
    "cpu_usage_rate",
    "cpu_usage_by_pod",
    "cpu_usage_by_deployment",
    "cpu_usage_by_node",
    "memory_usage",
    "memory_usage_by_deployment",
    "memory_working_set",
    "http_requests_rate",
    "http_errors_rate",
    "http_request_latency_p95",
    "pod_restarts",
    "pod_not_ready",
    "pod_count",
    "events_rate",
]


class MetricsQueryRequest(BaseModel):
    """
    Request model for metrics query.

    Prometheus query with namespace filtering.
    """

    query_type: str = Field(
        ...,
        description="Predefined query type",
        examples=["cpu_usage_rate", "memory_usage", "pod_status_up"],
    )

    env_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Environment name",
        examples=["dev", "staging", "prod"],
    )

    app_name: str = Field(
        default="cyoda", min_length=1, max_length=50, description="Application name"
    )

    time: Optional[str] = Field(
        None, description="Evaluation timestamp (RFC3339 or Unix timestamp)"
    )

    timeout: Optional[str] = Field(None, description="Query timeout (e.g., '30s')")

    @field_validator("query_type")
    @classmethod
    def validate_query_type(cls, v: str) -> str:
        """Validate query type is in allowed list."""
        if v not in VALID_QUERY_TYPES:
            raise ValueError(
                f"Invalid query_type. Must be one of: {', '.join(VALID_QUERY_TYPES)}"
            )
        return v

    @field_validator("env_name", "app_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate environment and app names."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.strip()


class MetricsRangeQueryRequest(BaseModel):
    """
    Request model for metrics range query.

    Prometheus range query with time bounds.
    """

    query_type: str = Field(..., description="Predefined query type")

    env_name: str = Field(
        ..., min_length=1, max_length=50, description="Environment name"
    )

    app_name: str = Field(
        default="cyoda", min_length=1, max_length=50, description="Application name"
    )

    start: str = Field(
        ...,
        description="Start timestamp (RFC3339 or Unix timestamp)",
        examples=["2025-12-01T00:00:00Z"],
    )

    end: str = Field(
        ...,
        description="End timestamp (RFC3339 or Unix timestamp)",
        examples=["2025-12-02T00:00:00Z"],
    )

    step: str = Field(
        default="15s", description="Query resolution step", examples=["15s", "1m", "5m"]
    )

    @field_validator("query_type")
    @classmethod
    def validate_query_type(cls, v: str) -> str:
        """Validate query type."""
        if v not in VALID_QUERY_TYPES:
            raise ValueError(
                f"Invalid query_type. Must be one of: {', '.join(VALID_QUERY_TYPES)}"
            )
        return v


class GrafanaTokenResponse(BaseModel):
    """
    Response model for Grafana token generation.

    Service account token with metadata.
    """

    token: str = Field(..., description="Grafana service account token")

    name: str = Field(..., description="Service account name")

    service_account_id: int = Field(..., description="Service account ID")

    grafana_url: str = Field(..., description="Grafana URL")

    namespace: str = Field(..., description="Kubernetes namespace")

    message: str = Field(..., description="Usage message")

    expires_in_days: int = Field(..., description="Days until expiration")


class PrometheusQueryResponse(BaseModel):
    """
    Response model for Prometheus query results.

    Standard Prometheus API response.
    """

    status: str = Field(..., description="Query status", examples=["success", "error"])

    data: Dict[str, Any] = Field(..., description="Query results")

    errorType: Optional[str] = Field(None, description="Error type if status is error")

    error: Optional[str] = Field(None, description="Error message if status is error")

    warnings: Optional[List[str]] = Field(None, description="Query warnings")


class MetricsHealthResponse(BaseModel):
    """
    Response model for metrics health check.

    Health status of Grafana and Prometheus services.
    """

    status: str = Field(
        ...,
        description="Overall health status",
        examples=["healthy", "degraded", "unhealthy"],
    )

    services: Dict[str, Dict[str, Any]] = Field(
        ..., description="Individual service health statuses"
    )
