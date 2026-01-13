"""Legacy GitHub API-based repository analysis.

This module provides repository analysis using GitHub API to fetch repository
structure and content, parsing entities, workflows, and requirements.
"""

import logging
from typing import Any, Optional

from quart.typing import ResponseReturnValue

from application.routes.common.response import APIResponse
from application.routes.repository_endpoints.models import (
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResponse,
    EntityResponse,
    RequirementResponse,
    WorkflowResponse,
)
from application.services import (
    get_github_service_for_private_repo,
    get_github_service_for_public_repo,
)
from application.services.repository_parser import RepositoryParser

logger = logging.getLogger(__name__)


def _get_github_service(
    installation_id: Optional[int], owner: str, repository_name: str
) -> Any:
    """Get appropriate GitHub service based on installation ID.

    Args:
        installation_id: GitHub installation ID.
        owner: Repository owner.
        repository_name: Repository name.

    Returns:
        GitHub service instance.
    """
    if installation_id:
        repository_url = f"https://github.com/{owner}/{repository_name}"
        github_service = get_github_service_for_private_repo(
            installation_id=installation_id,
            repository_url=repository_url,
            owner=owner,
        )
        logger.info(f"Using provided installation_id: {installation_id}")
    else:
        github_service = get_github_service_for_public_repo(owner=owner)
        logger.info("Using default public repo configuration")

    return github_service


async def _fetch_requirements_with_content(
    github_service: Any, structure: Any, repository_name: str, branch: str
) -> list[RequirementResponse]:
    """Fetch content for all requirements.

    Args:
        github_service: GitHub service instance.
        structure: Parsed repository structure.
        repository_name: Repository name.
        branch: Git branch.

    Returns:
        List of RequirementResponse objects with content.
    """
    requirements_with_content = []

    for r in structure.requirements:
        try:
            content = await github_service.contents.get_file_content(
                repository_name, r.file_path, ref=branch
            )
            requirements_with_content.append(
                RequirementResponse(
                    file_name=r.file_name, file_path=r.file_path, content=content
                )
            )
        except Exception as e:
            logger.error(f"Error fetching content for {r.file_path}: {e}")
            requirements_with_content.append(
                RequirementResponse(file_name=r.file_name, file_path=r.file_path)
            )

    return requirements_with_content


def _build_entity_responses(structure: Any) -> list[EntityResponse]:
    """Build entity response objects from structure.

    Args:
        structure: Parsed repository structure.

    Returns:
        List of EntityResponse objects.
    """
    return [
        EntityResponse(
            name=e.name,
            version=e.version,
            file_path=e.file_path,
            class_name=e.class_name,
            fields=e.fields,
            has_workflow=e.has_workflow,
        )
        for e in structure.entities
    ]


def _build_workflow_responses(structure: Any) -> list[WorkflowResponse]:
    """Build workflow response objects from structure.

    Args:
        structure: Parsed repository structure.

    Returns:
        List of WorkflowResponse objects.
    """
    return [
        WorkflowResponse(
            name=w.workflow_file or w.entity_name,
            entity_name=w.entity_name,
            file_path=w.file_path,
            content=None,
        )
        for w in structure.workflows
    ]


async def analyze_repository_legacy(
    req: AnalyzeRepositoryRequest,
) -> ResponseReturnValue:
    """Analyze repository using legacy GitHub API approach.

    Parses repository structure, fetches requirements content, and formats
    analysis results for API response.

    Args:
        req: Repository analysis request with owner, name, branch, and optional installation_id.

    Returns:
        API response with analysis results.
    """
    logger.info(
        f"Analyzing repository: {req.owner}/{req.repository_name} (branch: {req.branch})"
    )

    # Get GitHub service
    github_service = _get_github_service(
        req.installation_id, req.owner, req.repository_name
    )

    # Parse repository
    parser = RepositoryParser(github_service)
    structure = await parser.parse_repository(req.repository_name, req.branch)

    # Fetch requirements content
    requirements_with_content = await _fetch_requirements_with_content(
        github_service, structure, req.repository_name, req.branch
    )

    # Build response
    response = AnalyzeRepositoryResponse(
        repository_name=structure.repository_name,
        branch=structure.branch,
        app_type=structure.app_type,
        entities=_build_entity_responses(structure),
        workflows=_build_workflow_responses(structure),
        requirements=requirements_with_content,
    )

    logger.info(
        f"Successfully analyzed repository: {len(structure.entities)} entities, "
        f"{len(structure.workflows)} workflows, "
        f"{len(structure.requirements)} requirements"
    )

    return APIResponse.success(response.model_dump(by_alias=True))
