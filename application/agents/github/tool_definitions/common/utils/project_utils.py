"""Project type detection utilities for GitHub agent tools.

This module provides utilities for detecting project types (Python/Java)
and determining resource paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from ..constants import (
    PROJECT_TYPE_JAVA,
    PROJECT_TYPE_PYTHON,
    RESOURCE_TYPE_ENTITY,
    RESOURCE_TYPE_WORKFLOW,
)

# Resource paths from environment
PYTHON_RESOURCES_PATH = os.getenv("PYTHON_RESOURCES_PATH", "application/resources")
JAVA_RESOURCES_PATH = os.getenv("JAVA_RESOURCES_PATH", "src/main/resources")


def detect_project_type(repo_path: str) -> Dict[str, str]:
    """Detect project type (Python or Java) and return resource paths.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary containing:
        - type: "python" or "java"
        - resources_path: Base resources directory path
        - entities_path: Entities directory path
        - workflows_path: Workflows directory path
        - requirements_path: Functional requirements directory path

    Raises:
        ValueError: If project type cannot be detected
    """
    repo_path_obj = Path(repo_path)

    # Check for Python project
    if (repo_path_obj / "application").exists():
        return {
            "type": PROJECT_TYPE_PYTHON,
            "resources_path": PYTHON_RESOURCES_PATH,
            "entities_path": f"{PYTHON_RESOURCES_PATH}/{RESOURCE_TYPE_ENTITY}",
            "workflows_path": f"{PYTHON_RESOURCES_PATH}/{RESOURCE_TYPE_WORKFLOW}",
            "requirements_path": f"{PYTHON_RESOURCES_PATH}/functional_requirements",
        }

    # Check for Java project
    if (repo_path_obj / "src" / "main").exists():
        return {
            "type": PROJECT_TYPE_JAVA,
            "resources_path": JAVA_RESOURCES_PATH,
            "entities_path": f"{JAVA_RESOURCES_PATH}/{RESOURCE_TYPE_ENTITY}",
            "workflows_path": f"{JAVA_RESOURCES_PATH}/{RESOURCE_TYPE_WORKFLOW}",
            "requirements_path": f"{JAVA_RESOURCES_PATH}/functional_requirements",
        }

    raise ValueError(f"Could not detect project type in {repo_path}")
