"""Request and response models for repository endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from common.config.config import CLIENT_GIT_BRANCH


class AnalyzeRepositoryRequest(BaseModel):
    """Request model for repository analysis."""

    repository_name: str = Field(
        ..., description="Repository name (e.g., 'mcp-cyoda-quart-app')"
    )
    branch: str = Field(default=CLIENT_GIT_BRANCH, description="Branch name to analyze")
    owner: str = Field(default="Cyoda-platform", description="Repository owner")
    installation_id: Optional[int] = Field(
        default=None,
        description="GitHub App installation ID (optional, uses env var if not provided)",
    )


class EntityResponse(BaseModel):
    """Response model for entity information."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    version: int
    file_path: str = Field(..., alias="filePath")
    class_name: str = Field(..., alias="className")
    fields: List[Dict[str, Any]]
    has_workflow: bool = Field(..., alias="hasWorkflow")


class WorkflowResponse(BaseModel):
    """Response model for workflow information."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    entity_name: str = Field(..., alias="entityName")
    file_path: str = Field(..., alias="filePath")
    content: Optional[Dict[str, Any]] = None


class RequirementResponse(BaseModel):
    """Response model for requirement information."""

    model_config = ConfigDict(populate_by_name=True)

    file_name: str = Field(..., alias="fileName")
    file_path: str = Field(..., alias="filePath")
    content: Optional[str] = None


class AnalyzeRepositoryResponse(BaseModel):
    """Response model for repository analysis."""

    model_config = ConfigDict(populate_by_name=True)

    repository_name: str = Field(..., alias="repositoryName")
    branch: str
    app_type: str = Field(..., alias="appType")
    entities: List[EntityResponse]
    workflows: List[WorkflowResponse]
    requirements: List[RequirementResponse]
