"""
Request/Response models for logs routes.

Provides type-safe models for Elasticsearch log operations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class LogSearchRequest(BaseModel):
    """
    Request model for log search.

    Elasticsearch query with environment and application filtering.
    """

    env_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Environment name (e.g., 'dev', 'prod')",
        examples=["dev", "staging", "prod"]
    )

    app_name: str = Field(
        default="cyoda",
        min_length=1,
        max_length=50,
        description="Application name",
        examples=["cyoda", "my-app"]
    )

    query: Dict[str, Any] = Field(
        default_factory=lambda: {"match_all": {}},
        description="Elasticsearch query DSL",
        examples=[
            {"match_all": {}},
            {"match": {"level": "ERROR"}},
            {"range": {"@timestamp": {"gte": "now-1h"}}}
        ]
    )

    size: int = Field(
        default=50,
        ge=1,
        le=10000,
        description="Number of results to return (max 10000)"
    )

    sort: List[Dict[str, Any]] = Field(
        default_factory=lambda: [{"@timestamp": {"order": "desc"}}],
        description="Sort specification",
        examples=[[{"@timestamp": {"order": "desc"}}]]
    )

    @field_validator('env_name', 'app_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate environment and app names."""
        if not v or not v.strip():
            raise ValueError('Name cannot be empty or whitespace')
        # Allow alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Name must contain only alphanumeric characters, hyphens, and underscores')
        return v.strip()


class APIKeyResponse(BaseModel):
    """
    Response model for API key generation.

    Elasticsearch API key with metadata.
    """

    api_key: str = Field(
        ...,
        description="Base64-encoded Elasticsearch API key"
    )

    name: str = Field(
        ...,
        description="API key name"
    )

    created: bool = Field(
        ...,
        description="Whether key was newly created"
    )

    message: str = Field(
        ...,
        description="Usage message"
    )

    expires_in_days: int = Field(
        ...,
        description="Days until expiration"
    )


class LogSearchResponse(BaseModel):
    """
    Response model for log search results.

    Elasticsearch search results with hits.
    """

    hits: Dict[str, Any] = Field(
        ...,
        description="Search hits"
    )

    took: int = Field(
        ...,
        description="Time taken in milliseconds"
    )

    timed_out: bool = Field(
        ...,
        description="Whether query timed out"
    )

    _shards: Optional[Dict[str, Any]] = Field(
        None,
        description="Shard information"
    )


class HealthCheckResponse(BaseModel):
    """
    Response model for health check.

    ELK cluster health status.
    """

    status: str = Field(
        ...,
        description="Health status",
        examples=["healthy", "unhealthy", "degraded"]
    )

    elk_host: Optional[str] = Field(
        None,
        description="ELK host"
    )

    cluster_status: Optional[str] = Field(
        None,
        description="Cluster status",
        examples=["green", "yellow", "red"]
    )

    error: Optional[str] = Field(
        None,
        description="Error message if unhealthy"
    )
