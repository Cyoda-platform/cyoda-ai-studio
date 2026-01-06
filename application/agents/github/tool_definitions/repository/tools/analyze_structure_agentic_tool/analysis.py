"""Analysis functions for repository structure and content."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.utils.file_utils import is_textual_file
from application.agents.github.tool_definitions.repository.tools.execute_command_tool import execute_unix_command

from .validation import _extract_entity_name_and_version, _extract_workflow_name_and_version

logger = logging.getLogger(__name__)


async def _analyze_entity_files(
    entity_files: list[str],
    tool_context: ToolContext,
) -> list[dict]:
    """Analyze all entity files and extract their content.

    Args:
        entity_files: List of entity file paths.
        tool_context: Execution context.

    Returns:
        List of entity analysis results.
    """
    entities = []
    for entity_file in entity_files:
        entity_name, version = _extract_entity_name_and_version(entity_file)
        if not entity_name:
            continue

        cat_result = await execute_unix_command(f"cat '{entity_file}'", tool_context)
        cat_data = json.loads(cat_result)

        if not cat_data.get("success"):
            continue

        try:
            entity_content = json.loads(cat_data["stdout"])
            entities.append({
                "name": entity_name,
                "version": version,
                "path": entity_file,
                "content": entity_content
            })
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in entity file: {entity_file}")

    return entities


async def _analyze_workflow_files(
    workflow_files: list[str],
    tool_context: ToolContext,
) -> list[dict]:
    """Analyze all workflow files and extract their content.

    Args:
        workflow_files: List of workflow file paths.
        tool_context: Execution context.

    Returns:
        List of workflow analysis results.
    """
    workflows = []
    for workflow_file in workflow_files:
        workflow_name, version = _extract_workflow_name_and_version(workflow_file)

        cat_result = await execute_unix_command(f"cat '{workflow_file}'", tool_context)
        cat_data = json.loads(cat_result)

        if not cat_data.get("success"):
            continue

        try:
            workflow_content = json.loads(cat_data["stdout"])
            workflows.append({
                "name": workflow_name,
                "version": version,
                "path": workflow_file,
                "content": workflow_content
            })
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in workflow file: {workflow_file}")

    return workflows


async def _analyze_requirement_files(
    req_files: list[str],
    tool_context: ToolContext,
) -> list[dict]:
    """Analyze all requirements files and extract their content.

    Args:
        req_files: List of requirements file paths.
        tool_context: Execution context.

    Returns:
        List of requirements analysis results.
    """
    requirements = []
    for req_file in req_files:
        if not is_textual_file(Path(req_file).name):
            continue

        req_name = Path(req_file).stem

        cat_result = await execute_unix_command(f"cat '{req_file}'", tool_context)
        cat_data = json.loads(cat_result)

        if cat_data.get("success"):
            requirements.append({
                "name": req_name,
                "path": req_file,
                "content": cat_data["stdout"]
            })

    return requirements


async def _analyze_directory_structure(tool_context: ToolContext) -> list[str]:
    """Analyze repository directory structure.

    Args:
        tool_context: Execution context.

    Returns:
        List of relevant directories.
    """
    result = await execute_unix_command(
        "find . -type d | grep -E '(entity|workflow|functional_requirements)' | sort",
        tool_context
    )
    data = json.loads(result)

    if not data.get("success"):
        return []

    return [d.strip() for d in data["stdout"].split('\n') if d.strip()]


__all__ = [
    "_analyze_entity_files",
    "_analyze_workflow_files",
    "_analyze_requirement_files",
    "_analyze_directory_structure",
]
