"""Helper functions for repository analysis.

This module provides shared utility functions used by both conversation-based
and legacy analysis approaches.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from application.routes.repository_endpoints.helpers import is_textual_file
from application.services.repository_parser import RepositoryParser

logger = logging.getLogger(__name__)


async def _fetch_conversation(conversation_id: str) -> tuple[Optional[Dict[str, Any]], bool]:
    """Fetch conversation entity from entity service.

    Args:
        conversation_id: Technical ID of the conversation.

    Returns:
        Tuple of (conversation_data, success). Data is None if not found.
    """
    try:
        from application.entity.conversation.version_1.conversation import Conversation
        from services.services import get_entity_service

        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response or not response.data:
            logger.error(f"Conversation {conversation_id} not found")
            return None, False

        return response.data, True

    except Exception as e:
        logger.error(f"Failed to fetch conversation: {e}", exc_info=True)
        return None, False


def _extract_repository_info(conversation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract repository information from conversation data.

    Args:
        conversation_data: Conversation data (dict or object).

    Returns:
        Dictionary with extracted repository info keys.
    """
    if isinstance(conversation_data, dict):
        return {
            'repository_path': (
                conversation_data.get('workflow_cache', {})
                .get('adk_session_state', {})
                .get('repository_path')
            ),
            'repository_name': conversation_data.get('repository_name'),
            'repository_branch': conversation_data.get('repository_branch'),
            'repository_owner': conversation_data.get('repository_owner'),
            'repository_url': conversation_data.get('repository_url'),
            'installation_id': conversation_data.get('installation_id'),
        }
    else:
        return {
            'repository_path': (
                getattr(conversation_data, 'workflow_cache', {})
                .get('adk_session_state', {})
                .get('repository_path')
            ),
            'repository_name': getattr(conversation_data, 'repository_name', None),
            'repository_branch': getattr(conversation_data, 'repository_branch', None),
            'repository_owner': getattr(conversation_data, 'repository_owner', None),
            'repository_url': getattr(conversation_data, 'repository_url', None),
            'installation_id': getattr(conversation_data, 'installation_id', None),
        }


def _verify_repository_exists(repository_path: str) -> bool:
    """Verify repository exists and is a git repository.

    Args:
        repository_path: Path to repository.

    Returns:
        True if repository exists and is valid.
    """
    if not repository_path:
        return False

    repo_path_obj = Path(repository_path)
    return repo_path_obj.exists() and (repo_path_obj / ".git").exists()


async def _scan_repository_resources(
    repository_path: str,
) -> Dict[str, Any]:
    """Scan repository for entities, workflows, and requirements.

    Args:
        repository_path: Path to repository.

    Returns:
        Dictionary with entities, workflows, and requirements.
    """
    from application.agents.github.tools import _detect_project_type, _scan_versioned_resources

    paths = _detect_project_type(repository_path)
    repo_path_obj = Path(repository_path)

    # Scan entities
    entities_dir = repo_path_obj / paths["entities_path"]
    entities = _scan_versioned_resources(entities_dir, "entity", repo_path_obj)

    # Scan workflows
    workflows_dir = repo_path_obj / paths["workflows_path"]
    workflows = _scan_versioned_resources(workflows_dir, "workflow", repo_path_obj)

    return {
        "paths": paths,
        "entities": entities,
        "workflows": workflows,
        "repo_path_obj": repo_path_obj,
    }


async def _read_requirements(repo_path_obj: Path, requirements_path: str) -> list[Dict[str, Any]]:
    """Read requirements files from repository.

    Args:
        repo_path_obj: Path object of repository root.
        requirements_path: Relative path to requirements directory.

    Returns:
        List of requirement dictionaries with name, path, and content.
    """
    requirements: list[Dict[str, Any]] = []
    requirements_dir = repo_path_obj / requirements_path

    if not requirements_dir.exists():
        return requirements

    for req_file in sorted(requirements_dir.glob("*")):
        if not req_file.is_file() or not is_textual_file(req_file.name):
            continue

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


def _format_workflows_response(workflows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Format workflows for API response.

    Args:
        workflows: List of workflow data from scanner.

    Returns:
        List of formatted workflow dictionaries.
    """
    return [
        {
            "name": w.get("name", ""),
            "entityName": w.get("entity_name", ""),
            "filePath": w.get("path", ""),
            "content": w.get("content", {})
        }
        for w in workflows
    ]


def _format_analysis_response(
    repository_name: str,
    repository_branch: str,
    app_type: str,
    entities: list[Dict[str, Any]],
    workflows: list[Dict[str, Any]],
    requirements: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """Format analysis results for API response.

    Args:
        repository_name: Name of the repository.
        repository_branch: Git branch name.
        app_type: Application type (java or python).
        entities: List of entities.
        workflows: List of workflows.
        requirements: List of requirements.

    Returns:
        Formatted response dictionary.
    """
    return {
        "repositoryName": repository_name,
        "branch": repository_branch,
        "appType": app_type,
        "entities": entities,
        "workflows": _format_workflows_response(workflows),
        "requirements": requirements
    }
