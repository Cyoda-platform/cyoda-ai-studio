"""Conversation-based repository analysis.

This module provides repository analysis by retrieving repository information
from conversation entities and scanning the local repository directly.
"""

import logging

from quart.typing import ResponseReturnValue

from application.routes.common.response import APIResponse
from application.routes.repository_endpoints.helpers import ensure_repository_cloned

from .helpers import (
    _extract_repository_info,
    _fetch_conversation,
    _format_analysis_response,
    _read_requirements,
    _scan_repository_resources,
    _verify_repository_exists,
)

logger = logging.getLogger(__name__)


async def analyze_repository_conversation(conversation_id: str) -> ResponseReturnValue:
    """Analyze repository using conversation-based approach.

    Retrieves repository information from conversation, ensures repository is available
    (cloning if necessary), and scans for entities, workflows, and requirements.

    Args:
        conversation_id: Technical ID of the conversation.

    Returns:
        API response with analysis results or error.
    """
    logger.info(f"Analyzing repository for conversation: {conversation_id}")

    # Fetch conversation
    conversation_data, success = await _fetch_conversation(conversation_id)
    if not success:
        return APIResponse.error("Conversation not found", 404)

    # Extract repository information
    repo_info = _extract_repository_info(conversation_data)
    repository_path = repo_info["repository_path"]
    repository_name = repo_info["repository_name"]
    repository_branch = repo_info["repository_branch"]
    repository_owner = repo_info["repository_owner"]
    repository_url = repo_info["repository_url"]
    installation_id = repo_info["installation_id"]

    # Verify repository exists or clone if needed
    if not _verify_repository_exists(repository_path):
        if not repository_url or not repository_branch:
            return APIResponse.error(
                "Repository not available and insufficient information to clone. "
                "Please ensure the conversation has repository_url and repository_branch configured.",
                400,
            )

        logger.info(
            f"Repository not available at {repository_path}, attempting to clone from {repository_url}"
        )
        success, message, cloned_path = await ensure_repository_cloned(
            repository_url=repository_url,
            repository_branch=repository_branch,
            installation_id=installation_id,
            repository_name=repository_name,
            repository_owner=repository_owner,
            use_env_installation_id=True,
        )
        if not success:
            return APIResponse.error(f"Failed to clone repository: {message}", 400)

        repository_path = cloned_path
        logger.info(f"✅ Repository cloned successfully at {repository_path}")

    try:
        # Scan repository resources
        scan_results = await _scan_repository_resources(repository_path)
        paths = scan_results["paths"]
        entities = scan_results["entities"]
        workflows = scan_results["workflows"]
        repo_path_obj = scan_results["repo_path_obj"]

        # Read requirements
        requirements = await _read_requirements(
            repo_path_obj, paths["requirements_path"]
        )

        # Format and return response
        response = _format_analysis_response(
            repository_name=repository_name,
            repository_branch=repository_branch,
            app_type=paths["type"],
            entities=entities,
            workflows=workflows,
            requirements=requirements,
        )

        return APIResponse.success(response)

    except ValueError as e:
        return APIResponse.error(str(e), 400)
