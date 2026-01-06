"""Tool for analyzing repository structure.

This module handles analyzing the repository to extract entities, workflows, and requirements.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import STOP_ON_ERROR
from application.agents.github.tool_definitions.common.utils import ensure_repository_available
from application.agents.github.tool_definitions.common.utils.file_utils import is_textual_file
from application.agents.github.tool_definitions.common.utils.project_utils import detect_project_type
from application.agents.github.tool_definitions.repository.helpers import scan_versioned_resources
from application.agents.github.tool_definitions.repository.helpers._github_service import (
    get_entity_service,
)
from application.entity.conversation import Conversation

logger = logging.getLogger(__name__)


async def _extract_repository_info(tool_context: ToolContext) -> tuple[bool, str, str, str, str]:
    """Extract repository info from context or conversation entity.

    Args:
        tool_context: Execution context

    Returns:
        Tuple of (success, error_msg, repository_name, repository_branch, repository_owner)
    """
    conversation_id = tool_context.state.get("conversation_id")
    if not conversation_id:
        return False, f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}", "", "", ""

    # Try context state first
    repository_name = tool_context.state.get("repository_name")
    repository_branch = tool_context.state.get("branch_name")
    repository_owner = tool_context.state.get("repository_owner")

    # Fallback to Conversation entity
    if not repository_name or not repository_branch:
        entity_service = get_entity_service()
        conversation_response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not conversation_response:
            return False, f"ERROR: Conversation {conversation_id} not found.{STOP_ON_ERROR}", "", "", ""

        conversation_data = conversation_response.data
        if isinstance(conversation_data, dict):
            repository_name = repository_name or conversation_data.get('repository_name')
            repository_branch = repository_branch or conversation_data.get('repository_branch')
            repository_owner = repository_owner or conversation_data.get('repository_owner')
        else:
            repository_name = repository_name or getattr(conversation_data, 'repository_name', None)
            repository_branch = repository_branch or getattr(conversation_data, 'repository_branch', None)
            repository_owner = repository_owner or getattr(conversation_data, 'repository_owner', None)

    if not repository_name or not repository_branch:
        return False, f"ERROR: No repository configured for this conversation.{STOP_ON_ERROR}", "", "", ""

    return True, "", repository_name, repository_branch, repository_owner


async def _scan_resources(
    repository_path: str, paths: Dict[str, str]
) -> tuple[list, list, list]:
    """Scan repository resources (entities, workflows, requirements).

    Args:
        repository_path: Path to repository
        paths: Project paths config

    Returns:
        Tuple of (entities, workflows, requirements)
    """
    repo_path_obj = Path(repository_path)
    loop = asyncio.get_event_loop()

    logger.info("🔍 Starting comprehensive resource scan...")

    # Scan entities
    entities_dir = repo_path_obj / paths["entities_path"]
    entities = await loop.run_in_executor(
        None, scan_versioned_resources, entities_dir, "entity", repo_path_obj
    )

    # Scan workflows
    workflows_dir = repo_path_obj / paths["workflows_path"]
    workflows = await loop.run_in_executor(
        None, scan_versioned_resources, workflows_dir, "workflow", repo_path_obj
    )

    # Scan requirements
    requirements_dir = repo_path_obj / paths["requirements_path"]

    def _read_requirements():
        requirements = []
        if requirements_dir.exists():
            for req_file in sorted(requirements_dir.glob("*")):
                if req_file.is_file() and is_textual_file(req_file.name):
                    try:
                        with open(req_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        requirements.append({
                            "name": req_file.stem,
                            "path": str(req_file.relative_to(repo_path_obj)),
                            "content": content,
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read requirement {req_file}: {e}")
        return requirements

    requirements = await loop.run_in_executor(None, _read_requirements)

    return entities, workflows, requirements


def _build_version_map(items: list, item_key: str) -> tuple[set, dict]:
    """Build version map for items.

    Args:
        items: List of items
        item_key: Key to extract name from item

    Returns:
        Tuple of (unique_names, version_map)
    """
    unique_names = set()
    version_map = {}

    for item in items:
        name = item[item_key]
        unique_names.add(name)
        if name not in version_map:
            version_map[name] = []
        version = item['version'] or 'direct'
        version_map[name].append(version)

    return unique_names, version_map


def _log_version_info(resource_type: str, version_map: dict) -> None:
    """Log version information for a resource type.

    Args:
        resource_type: Type of resource (Entity, Workflow)
        version_map: Map of resource names to versions
    """
    if not version_map:
        logger.info(f"📋 No {resource_type.lower()}s found in repository")
        return

    logger.info(f"📋 {resource_type} versions found:")
    for name, versions in sorted(version_map.items()):
        clean_versions = [v for v in versions if v != 'direct']
        direct_files = [v for v in versions if v == 'direct']
        version_info = []
        if clean_versions:
            version_info.extend(sorted(clean_versions))
        if direct_files:
            version_info.append('(direct file)')
        logger.info(f"   - {name}: {', '.join(version_info)}")


def _count_and_log_resources(entities: list, workflows: list, requirements: list) -> None:
    """Count resources and log summary.

    Args:
        entities: List of entities
        workflows: List of workflows
        requirements: List of requirements
    """
    unique_entities, entity_versions = _build_version_map(entities, 'name')
    unique_workflows, workflow_versions = _build_version_map(workflows, 'name')

    logger.info(
        f"✅ Repository analysis complete: "
        f"{len(unique_entities)} unique entities ({len(entities)} total versions), "
        f"{len(unique_workflows)} unique workflows ({len(workflows)} total versions), "
        f"{len(requirements)} requirements"
    )

    _log_version_info("Entity", entity_versions)
    _log_version_info("Workflow", workflow_versions)


def _build_result_structure(
    paths: Dict[str, str],
    repository_owner: str,
    repository_name: str,
    repository_branch: str,
) -> Dict[str, Any]:
    """Build initial result structure for repository analysis.

    Args:
        paths: Project paths configuration
        repository_owner: Repository owner
        repository_name: Repository name
        repository_branch: Branch name

    Returns:
        Result dictionary with empty lists for resources
    """
    return {
        "project_type": paths["type"],
        "repository": {
            "owner": repository_owner or "unknown",
            "name": repository_name,
            "branch": repository_branch,
        },
        "entities": [],
        "workflows": [],
        "requirements": [],
    }


async def _setup_repository_context(
    tool_context: ToolContext,
) -> tuple[bool, str, str, str, str, str]:
    """Setup and validate repository context.

    Args:
        tool_context: Tool context

    Returns:
        Tuple of (success, error_msg, repository_path, repository_name,
                  repository_branch, repository_owner)
    """
    # Extract repository info
    success, error_msg, repository_name, repository_branch, repository_owner = (
        await _extract_repository_info(tool_context)
    )
    if not success:
        return False, error_msg, "", "", "", ""

    # Get and validate repository path
    repository_path = tool_context.state.get("repository_path")
    if not repository_path:
        error = f"ERROR: repository_path not found in context. Repository must be cloned first.{STOP_ON_ERROR}"
        return False, error, "", "", "", ""

    # Ensure repository is available locally
    success, message, repository_path = await ensure_repository_available(
        repository_path=repository_path,
        tool_context=tool_context,
        require_git=True,
    )

    if not success:
        return False, f"ERROR: {message}{STOP_ON_ERROR}", "", "", "", ""

    return True, "", repository_path, repository_name, repository_branch, repository_owner


async def analyze_repository_structure(tool_context: ToolContext) -> str:
    """Analyze repository structure and return entities, workflows, and requirements.

    Auto-detects Python vs Java project and returns structured JSON with:
    - Project type (python/java)
    - List of entities with their JSON content
    - List of workflows with their JSON content
    - List of functional requirements (markdown files)

    Args:
        tool_context: The ADK tool context

    Returns:
        JSON string with repository structure
    """
    try:
        # Setup and validate repository context
        success, error_msg, repository_path, repository_name, repository_branch, repository_owner = (
            await _setup_repository_context(tool_context)
        )
        if not success:
            return error_msg

        # Detect project type
        try:
            paths = detect_project_type(repository_path)
        except ValueError as e:
            return f"ERROR: {str(e)}"

        # Build result structure
        result = _build_result_structure(
            paths, repository_owner, repository_name, repository_branch
        )

        # Scan all resources
        entities, workflows, requirements = await _scan_resources(repository_path, paths)
        result["entities"] = entities
        result["workflows"] = workflows
        result["requirements"] = requirements

        # Count and log results
        _count_and_log_resources(entities, workflows, requirements)

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error analyzing repository structure: {e}", exc_info=True)
        return f"ERROR: {str(e)}"
