"""Analyze repository endpoint.

This module is organized into focused submodules:
- helpers: Shared utility functions for repository analysis
- legacy_analysis: GitHub API-based analysis approach
- conversation_analysis: Conversation-based analysis approach
"""

from __future__ import annotations

import logging

from quart import request
from quart.typing import ResponseReturnValue

from application.routes.common.response import APIResponse
from application.routes.repository_endpoints.models import AnalyzeRepositoryRequest

# Re-export dependencies (for test mocking)
from application.services import (
    get_github_service_for_private_repo,
    get_github_service_for_public_repo,
)
from application.services.repository_parser import RepositoryParser
from services.services import get_entity_service

# Re-export all public APIs from submodules
from .helpers import (
    _fetch_conversation,
    _extract_repository_info,
    _verify_repository_exists,
    _scan_repository_resources,
    _read_requirements,
    _format_workflows_response,
    _format_analysis_response,
)

from .legacy_analysis import (
    _get_github_service,
    _fetch_requirements_with_content,
    _build_entity_responses,
    _build_workflow_responses,
    analyze_repository_legacy,
)

from .conversation_analysis import (
    analyze_repository_conversation,
)

logger = logging.getLogger(__name__)


async def handle_analyze_repository() -> ResponseReturnValue:
    """Handle analyze repository endpoint."""
    try:
        data = await request.get_json()
        conversation_id = data.get("conversation_id")

        if conversation_id:
            return await analyze_repository_conversation(conversation_id)

        req = AnalyzeRepositoryRequest(**data)
        return await analyze_repository_legacy(req)

    except Exception as e:
        logger.error(f"Error analyzing repository: {e}", exc_info=True)
        return APIResponse.error(
            "Failed to analyze repository",
            500,
            details={"message": str(e)}
        )


__all__ = [
    # Dependencies (for test mocking)
    "get_github_service_for_private_repo",
    "get_github_service_for_public_repo",
    "RepositoryParser",
    "get_entity_service",
    # Helpers
    "_fetch_conversation",
    "_extract_repository_info",
    "_verify_repository_exists",
    "_scan_repository_resources",
    "_read_requirements",
    "_format_workflows_response",
    "_format_analysis_response",
    # Legacy analysis
    "_get_github_service",
    "_fetch_requirements_with_content",
    "_build_entity_responses",
    "_build_workflow_responses",
    "analyze_repository_legacy",
    # Conversation analysis
    "analyze_repository_conversation",
    # Main handler
    "handle_analyze_repository",
]
