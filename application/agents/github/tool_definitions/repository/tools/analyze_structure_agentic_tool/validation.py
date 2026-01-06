"""Validation functions for repository analysis."""

from __future__ import annotations

import logging
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def _validate_context_and_path(tool_context: ToolContext) -> tuple[str, str]:
    """Validate tool context and extract repository path.

    Args:
        tool_context: Execution context.

    Returns:
        Tuple of (error_msg, repository_path). Error is empty if valid.

    Raises:
        ValueError: If context or path is invalid.
    """
    if not tool_context:
        raise ValueError("Tool context not available")

    repository_path = tool_context.state.get("repository_path")
    if not repository_path:
        raise ValueError("Repository path not found in context")

    return repository_path


def _extract_entity_name_and_version(entity_file: str) -> tuple[str, str]:
    """Extract entity name and version from file path.

    Args:
        entity_file: Path to entity file.

    Returns:
        Tuple of (entity_name, version). Version is None if not found.
    """
    path_parts = entity_file.split('/')
    if 'entity' not in path_parts:
        return None, None

    entity_idx = path_parts.index('entity')
    if entity_idx + 1 >= len(path_parts):
        return None, None

    entity_name = path_parts[entity_idx + 1]
    version = None

    if entity_idx + 2 < len(path_parts) and path_parts[entity_idx + 2].startswith('version_'):
        version = path_parts[entity_idx + 2]

    return entity_name, version


def _extract_workflow_name_and_version(workflow_file: str) -> tuple[str, str]:
    """Extract workflow name and version from file path.

    Args:
        workflow_file: Path to workflow file.

    Returns:
        Tuple of (workflow_name, version). Version is None if not found.
    """
    workflow_name = Path(workflow_file).stem
    version = None

    path_parts = workflow_file.split('/')
    for part in path_parts:
        if part.startswith('version_'):
            version = part
            break

    return workflow_name, version


def _initialize_results(repository_path: str) -> dict:
    """Initialize empty analysis results structure.

    Args:
        repository_path: Path to repository being analyzed.

    Returns:
        Initialized analysis results dictionary.
    """
    return {
        "analysis_type": "agentic_unix_based",
        "repository_path": repository_path,
        "commands_executed": [],
        "entities": [],
        "workflows": [],
        "requirements": [],
        "structure": {},
        "summary": {}
    }


def _generate_analysis_summary(
    entities: list[dict],
    workflows: list[dict],
    requirements: list[dict],
    commands_executed: list[dict],
) -> dict:
    """Generate summary statistics for analysis results.

    Args:
        entities: List of analyzed entities.
        workflows: List of analyzed workflows.
        requirements: List of analyzed requirements.
        commands_executed: List of executed commands.

    Returns:
        Summary dictionary with key statistics.
    """
    unique_entities = {entity["name"] for entity in entities}
    unique_workflows = {workflow["name"] for workflow in workflows}

    return {
        "unique_entities": len(unique_entities),
        "total_entity_versions": len(entities),
        "unique_workflows": len(unique_workflows),
        "total_workflow_versions": len(workflows),
        "requirements_files": len(requirements),
        "commands_executed": len(commands_executed)
    }


__all__ = [
    "_validate_context_and_path",
    "_extract_entity_name_and_version",
    "_extract_workflow_name_and_version",
    "_initialize_results",
    "_generate_analysis_summary",
]
