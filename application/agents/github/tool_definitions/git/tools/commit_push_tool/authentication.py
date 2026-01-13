"""Authentication handling and URL updates for git operations."""

from __future__ import annotations

import asyncio
import logging

from google.adk.tools.tool_context import ToolContext

from .git_operations import _push_to_branch

logger = logging.getLogger(__name__)


async def _get_repo_url_and_installation_id(
    repository_type: str, language: str, user_repository_url: str, installation_id: str
) -> tuple[str | None, str | None]:
    """Get repository URL and installation ID based on type.

    Args:
        repository_type: Type of repository (public or private)
        language: Programming language
        user_repository_url: User's repository URL
        installation_id: GitHub installation ID

    Returns:
        Tuple of (repo_url, installation_id) or (None, None) if not applicable
    """
    if repository_type == "private" and user_repository_url and installation_id:
        logger.info(f"🔐 Using private repository: {user_repository_url}")
        return user_repository_url, installation_id

    if repository_type == "public":
        from common.config.config import (
            GITHUB_PUBLIC_REPO_INSTALLATION_ID,
            JAVA_PUBLIC_REPO_URL,
            PYTHON_PUBLIC_REPO_URL,
        )

        repo_url = (
            PYTHON_PUBLIC_REPO_URL
            if language.lower() == "python"
            else JAVA_PUBLIC_REPO_URL if language.lower() == "java" else None
        )
        logger.info(f"🔐 Using public repository: {repo_url}")
        return repo_url, GITHUB_PUBLIC_REPO_INSTALLATION_ID

    return None, None


async def _update_remote_url(
    repository_path: str, repo_url: str, installation_id: str
) -> bool:
    """Update git remote URL with fresh authentication.

    Args:
        repository_path: Path to repository
        repo_url: Repository URL
        installation_id: GitHub installation ID

    Returns:
        True if successful, False otherwise
    """
    try:
        from application.agents.shared.repository_tools import (
            _get_authenticated_repo_url_sync,
        )

        authenticated_url = await _get_authenticated_repo_url_sync(
            repo_url, installation_id
        )

        process = await asyncio.create_subprocess_exec(
            "git",
            "remote",
            "set-url",
            "origin",
            authenticated_url,
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            logger.warning(f"⚠️ Failed to update remote URL: {error_msg}")
            return False

        logger.info("✅ Successfully refreshed remote authentication")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Failed to refresh authentication: {e}")
        return False


async def _refresh_auth_and_push(
    repository_path: str, branch_name: str, tool_context: ToolContext
) -> tuple[bool, str]:
    """Refresh authentication and push changes.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Execution context

    Returns:
        Tuple of (success, error_message)
    """
    repository_type = tool_context.state.get("repository_type")
    user_repository_url = tool_context.state.get("user_repository_url")
    installation_id = tool_context.state.get("installation_id")
    language = tool_context.state.get("language", "python")

    repo_url, inst_id = await _get_repo_url_and_installation_id(
        repository_type, language, user_repository_url, installation_id
    )

    if repo_url and inst_id:
        await _update_remote_url(repository_path, repo_url, inst_id)

    return await _push_to_branch(repository_path, branch_name)
