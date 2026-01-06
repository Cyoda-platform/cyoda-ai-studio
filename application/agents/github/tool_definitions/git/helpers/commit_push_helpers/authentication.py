"""Authentication and credential management for git operations.

This module handles authentication extraction, validation, and URL refresh
for git commit and push operations.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import (
    AUTH_REFRESH_TIMEOUT,
    GIT_CMD,
    GIT_ORIGIN,
    GIT_REMOTE,
)
from application.agents.shared.repository_tools import _get_authenticated_repo_url_sync

logger = logging.getLogger(__name__)


@dataclass
class CommitContext:
    """Context for commit and push operations."""

    repository_path: str
    branch_name: str
    tool_context: Optional[ToolContext] = None
    repo_url: Optional[str] = None
    installation_id: Optional[str] = None
    repository_type: Optional[str] = None


def _extract_auth_from_context(
    context: CommitContext,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract authentication info from commit context.

    Args:
        context: Commit context

    Returns:
        Tuple of (repository_type, repo_url, installation_id)
    """
    if not context.tool_context:
        return context.repository_type, context.repo_url, context.installation_id

    repository_type = context.repository_type or context.tool_context.state.get(
        "repository_type"
    )
    repo_url = context.repo_url or context.tool_context.state.get("user_repository_url")
    installation_id = context.installation_id or context.tool_context.state.get(
        "installation_id"
    )

    logger.info(
        f"🔐 Auth info - type: {repository_type}, repo_url: {repo_url}, inst_id: {installation_id}"
    )

    return repository_type, repo_url, installation_id


def _validate_auth_params(
    repository_type: Optional[str],
    repo_url: Optional[str],
    installation_id: Optional[str],
) -> tuple[bool, Optional[str]]:
    """Validate authentication parameters.

    Args:
        repository_type: Repository type
        repo_url: Repository URL
        installation_id: GitHub App installation ID

    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_params = []

    if not repo_url:
        missing_params.append("repo_url (Repository URL for GitHub App authentication)")
    if not installation_id:
        missing_params.append("installation_id (GitHub App installation ID)")
    if not repository_type:
        missing_params.append("repository_type (Repository type: 'public' or 'private')")

    if missing_params:
        error_msg = (
            f"❌ Missing required authentication parameters: {', '.join(missing_params)}"
        )
        return False, error_msg

    return True, None


async def _get_authenticated_url_with_timeout(
    repo_url: str, installation_id: str
) -> Optional[str]:
    """Get authenticated repository URL with timeout handling.

    Args:
        repo_url: Repository URL
        installation_id: GitHub App installation ID

    Returns:
        Authenticated URL or None if failed
    """
    try:
        authenticated_url = await asyncio.wait_for(
            _get_authenticated_repo_url_sync(repo_url, installation_id),
            timeout=AUTH_REFRESH_TIMEOUT,
        )
        logger.info("🔐 Got authenticated URL successfully")
        return authenticated_url
    except asyncio.TimeoutError:
        logger.error(
            f"❌ Timeout getting authenticated URL ({AUTH_REFRESH_TIMEOUT}s) - "
            "will attempt push without auth refresh"
        )
        return None
    except Exception as e:
        logger.error(
            f"❌ Failed to get authenticated URL: {e} - "
            "will attempt push without auth refresh"
        )
        return None


async def _update_git_remote_url(
    repository_path: str, authenticated_url: str
) -> bool:
    """Update git remote origin URL with authenticated credentials.

    Args:
        repository_path: Path to repository
        authenticated_url: Authenticated repository URL

    Returns:
        True if successful, False otherwise
    """
    logger.info("🔐 Updating git remote URL with authenticated credentials")
    set_url_process = await asyncio.create_subprocess_exec(
        GIT_CMD,
        GIT_REMOTE,
        "set-url",
        GIT_ORIGIN,
        authenticated_url,
        cwd=repository_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await set_url_process.communicate()
    logger.info(f"🔐 git remote set-url returncode: {set_url_process.returncode}")

    if set_url_process.returncode != 0:
        error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
        logger.warning(f"⚠️ Failed to update remote URL: {error_msg}")
        return False

    logger.info("✅ Successfully updated git remote with authenticated URL")
    return True


async def _refresh_git_authentication(
    repository_path: str, repo_url: str, installation_id: str
) -> bool:
    """Refresh git remote authentication with fresh token.

    Args:
        repository_path: Path to repository
        repo_url: Repository URL
        installation_id: GitHub App installation ID

    Returns:
        True if successful, False otherwise
    """
    logger.info(
        f"🔐 Refreshing authentication - repo_url: {repo_url}, inst_id: {installation_id}"
    )

    # Step 1: Get authenticated URL
    authenticated_url = await _get_authenticated_url_with_timeout(repo_url, installation_id)
    if not authenticated_url:
        return False

    # Step 2: Update remote URL with authenticated credentials
    return await _update_git_remote_url(repository_path, authenticated_url)
