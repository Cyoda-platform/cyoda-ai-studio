"""Data Transfer Objects for deployment operations.

This module provides Pydantic models to encapsulate related arguments,
reducing function parameter count and improving code clarity.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DeployUserApplicationRequest(BaseModel):
    """DTO for user application deployment requests."""

    repository_url: str = Field(
        ..., description="Git repository URL containing the application code"
    )
    branch_name: str = Field(..., description="Git branch to deploy")
    cyoda_client_id: str = Field(..., description="Cyoda client ID for authentication")
    cyoda_client_secret: str = Field(
        ..., description="Cyoda client secret for authentication"
    )
    env_name: str = Field(..., description="Environment name to deploy to")
    app_name: str = Field(..., description="Application name for this deployment")
    is_public: bool = Field(
        default=True, description="Whether the repository is public"
    )
    installation_id: Optional[str] = Field(
        default=None, description="GitHub installation ID for public repos"
    )


class DeploymentConfig(BaseModel):
    """DTO for deployment configuration and tracking."""

    build_id: str = Field(..., description="The deployment build ID")
    namespace: str = Field(..., description="The deployment namespace")
    deployment_type: str = Field(
        ..., description="Type of deployment (e.g., 'environment_deployment')"
    )
    task_name: str = Field(..., description="Name for the background task")
    task_description: str = Field(
        ..., description="Description for the background task"
    )
    env_url: Optional[str] = Field(default=None, description="Optional environment URL")
    additional_metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional additional metadata to include in task"
    )


class SearchLogsRequest(BaseModel):
    """DTO for log search requests."""

    env_name: str = Field(..., description="Environment name to search logs in")
    query: Optional[str] = Field(default=None, description="Search query/pattern")
    app_name: Optional[str] = Field(
        default=None, description="Filter by application name"
    )
    level: Optional[str] = Field(
        default=None, description="Filter by log level (INFO, ERROR, etc.)"
    )
    start_time: Optional[str] = Field(
        default=None, description="Start time for log range"
    )
    end_time: Optional[str] = Field(default=None, description="End time for log range")
    limit: int = Field(
        default=100, description="Maximum number of log entries to return"
    )


class DeployCyodaEnvironmentRequest(BaseModel):
    """DTO for Cyoda environment deployment requests."""

    env_name: str = Field(
        ..., description="Environment name/namespace to use for deployment"
    )
    build_id: Optional[str] = Field(
        default=None, description="Optional build ID to associate with deployment"
    )
