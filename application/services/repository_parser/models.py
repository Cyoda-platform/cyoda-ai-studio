"""Data models for repository parsing."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EntityInfo:
    """Information about an entity in the repository."""

    name: str
    version: int
    file_path: str
    class_name: str
    fields: List[Dict[str, Any]]
    has_workflow: bool = False


@dataclass
class WorkflowInfo:
    """Information about a workflow in the repository."""

    entity_name: str
    file_path: str
    version: Optional[int] = None
    workflow_file: Optional[str] = None


@dataclass
class RequirementInfo:
    """Information about a functional requirement."""

    file_name: str
    file_path: str
    content: Optional[str] = None


@dataclass
class RepositoryStructure:
    """Complete repository structure."""

    app_type: str  # "python" or "java"
    entities: List[EntityInfo]
    workflows: List[WorkflowInfo]
    requirements: List[RequirementInfo]
    branch: str
    repository_name: str
