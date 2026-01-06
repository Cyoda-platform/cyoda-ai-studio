"""
Repository routes for analyzing GitHub repositories.

Provides endpoints to analyze Cyoda application repositories and extract
entities, workflows, and functional requirements.

This is a thin routes file that delegates to endpoint handlers in the
repository_endpoints package.
"""

from quart import Blueprint
from quart.typing import ResponseReturnValue

from application.routes.repository_endpoints import (
    handle_analyze_repository,
    handle_get_file_content,
    handle_get_repository_diff,
    handle_health_check,
    handle_pull_repository,
)
from application.routes.repository_endpoints.helpers import ensure_repository_cloned as _ensure_repository_cloned

repository_bp = Blueprint("repository", __name__, url_prefix="/api/v1/repository")



@repository_bp.route("/analyze", methods=["POST"])
async def analyze_repository() -> ResponseReturnValue:
    """Analyze a GitHub repository to extract Cyoda application structure."""
    return await handle_analyze_repository()


@repository_bp.route("/file-content", methods=["POST"])
async def get_file_content() -> ResponseReturnValue:
    """Get file content from GitHub repository."""
    return await handle_get_file_content()


@repository_bp.route("/diff", methods=["POST"])
async def get_repository_diff() -> ResponseReturnValue:
    """Get diff of uncommitted changes in a repository."""
    return await handle_get_repository_diff()


@repository_bp.route("/pull", methods=["POST"])
async def pull_repository() -> ResponseReturnValue:
    """Pull latest changes from remote repository."""
    return await handle_pull_repository()


@repository_bp.route("/health", methods=["GET"])
async def health_check() -> ResponseReturnValue:
    """Health check endpoint for repository service."""
    return await handle_health_check()
