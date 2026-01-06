"""Clone operations and repository setup.

This module handles repository URL determination, path building, validation,
and the actual clone and branch setup workflow.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.constants import (
    PROTECTED_BRANCHES,
    JAVA_TEMPLATE_REPO,
    PYTHON_TEMPLATE_REPO,
)
from application.agents.shared.repository_tools.git_operations import (
    _get_authenticated_repo_url_sync,
)
from application.agents.shared.repository_tools.validation import (
    _is_protected_branch,
    _validate_clone_parameters,
)
from ..context import _store_in_tool_context
from ..git_ops import _clone_repo_to_path, _push_branch_to_remote
from .branch_handlers import _handle_branch_setup

logger = logging.getLogger(__name__)


async def _handle_already_cloned_repo(
    tool_context: Optional[ToolContext],
    target_directory: str,
    branch_name: str,
    language: str,
    repository_name: str,
    repository_owner: str,
    user_repo_url: Optional[str],
    installation_id: Optional[str],
    repo_type: Optional[str]
) -> str:
    """Handle case where repository is already cloned.

    Args:
        tool_context: Tool context
        target_directory: Repository path
        branch_name: Branch name
        language: Programming language
        repository_name: Repository name
        repository_owner: Repository owner
        user_repo_url: User's repository URL
        installation_id: GitHub installation ID
        repo_type: Repository type

    Returns:
        Success message
    """
    logger.info(f"Repository already exists at {target_directory}, skipping clone")

    if tool_context:
        _store_in_tool_context(
            tool_context,
            target_directory,
            branch_name,
            language,
            repository_name,
            repository_owner,
            user_repo_url,
            installation_id,
            repo_type
        )

    return f"SUCCESS: Repository already exists at {target_directory} on branch {branch_name}"


async def _build_target_path(
    target_directory: Optional[str],
    branch_name: str
) -> Path:
    """Build and create target directory path.

    Args:
        target_directory: Optional target directory
        branch_name: Branch name

    Returns:
        Target path
    """
    if target_directory is None:
        builds_dir = Path("/tmp/cyoda_builds")
        builds_dir.mkdir(parents=True, exist_ok=True)
        target_directory = str(builds_dir / branch_name)

    target_path = Path(target_directory)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


async def _determine_repo_url(
    language: str,
    user_repo_url: Optional[str],
    installation_id: Optional[str]
) -> tuple[str, bool]:
    """Determine repository URL to clone from.

    Args:
        language: Programming language
        user_repo_url: User's repository URL
        installation_id: GitHub installation ID

    Returns:
        Tuple of (repo_url, is_user_repo)
    """
    if user_repo_url and installation_id:
        repo_url = await _get_authenticated_repo_url_sync(user_repo_url, installation_id)
        logger.info(f"🔐 Cloning from user's repository: {user_repo_url}")
        return repo_url, True

    # Use template repositories
    if language.lower() == "java":
        repo_url = JAVA_TEMPLATE_REPO
    elif language.lower() == "python":
        repo_url = PYTHON_TEMPLATE_REPO
    else:
        raise ValueError(f"Unsupported language '{language}'. Supported: java, python")

    logger.warning(f"⚠️ No user repository configured, cloning from template: {repo_url}")
    return repo_url, False


async def _validate_and_check_protected_branch(branch_name: str) -> Optional[str]:
    """Validate branch name and check if protected.

    Args:
        branch_name: Branch name to validate

    Returns:
        Error message if invalid, None if valid
    """
    _validate_clone_parameters("python", branch_name)

    if await _is_protected_branch(branch_name):
        error_msg = (
            f"🚫 CRITICAL ERROR: Cannot use protected branch '{branch_name}'. "
            f"Protected branches ({', '.join(sorted(PROTECTED_BRANCHES))}) "
            f"must NEVER be used for builds. Use generate_branch_uuid()."
        )
        logger.error(error_msg)
        return f"ERROR: {error_msg}"

    return None


def _extract_repo_name_and_owner(user_repo_url: Optional[str]) -> tuple[str, str]:
    """Extract repository name and owner from GitHub URL.

    Returns:
        Tuple of (repository_owner, repository_name)
    """
    repository_name = "mcp-cyoda-quart-app"  # Default
    repository_owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")  # Default

    if user_repo_url:
        # Pattern to match: https://github.com/owner/repo or https://github.com/owner/repo.git
        match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(\.git)?$', user_repo_url)
        if match:
            repository_owner = match.group(1)
            repository_name = match.group(2)
            logger.info(f"📦 Extracted from URL: {repository_owner}/{repository_name}")
        else:
            # Fallback: just extract repo name
            match = re.search(r'/([^/]+?)(\.git)?$', user_repo_url)
            if match:
                repository_name = match.group(1)
                logger.info(f"📦 Extracted repository name from URL: {repository_name}")

    return repository_owner, repository_name


async def _setup_repository_clone(
    language: str,
    user_repo_url: Optional[str],
    installation_id: Optional[str],
    repo_type: Optional[str],
    target_directory: Optional[str],
    branch_name: str,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Setup repository clone operation.

    Args:
        language: Programming language
        user_repo_url: User repository URL
        installation_id: Installation ID
        repo_type: Repository type
        target_directory: Target directory
        branch_name: Branch name

    Returns:
        Tuple of (repo_url, target_directory, repository_owner, repository_name, error_msg)
    """
    try:
        repo_url, _ = await _determine_repo_url(language, user_repo_url, installation_id)
    except ValueError as e:
        return None, None, None, None, f"ERROR: {str(e)}"

    target_path = await _build_target_path(target_directory, branch_name)
    target_directory = str(target_path)
    repository_owner, repository_name = _extract_repo_name_and_owner(user_repo_url)

    return repo_url, target_directory, repository_owner, repository_name, None


async def _perform_clone_and_branch(
    repo_url: str,
    target_path: Path,
    branch_name: str,
    use_existing_branch: bool,
    user_repo_url: Optional[str],
) -> Optional[str]:
    """Perform clone and branch operations.

    Args:
        repo_url: Repository URL to clone
        target_path: Target directory path
        branch_name: Branch name
        use_existing_branch: Whether to use existing branch
        user_repo_url: User repository URL

    Returns:
        Error message if failed, None if successful
    """
    logger.info(f"Cloning repository to {target_path}")
    success, error_msg = await _clone_repo_to_path(repo_url, target_path)
    if not success:
        return f"ERROR: Failed to clone repository: {error_msg}"

    error_msg = await _handle_branch_setup(
        target_path, branch_name, use_existing_branch, user_repo_url
    )
    if error_msg:
        return error_msg

    logger.info(f"✅ Successfully cloned repository to {target_path}")
    return None


async def _handle_push_and_finalize(
    target_path: Path,
    branch_name: str,
    use_existing_branch: bool,
    user_repo_url: Optional[str],
    installation_id: Optional[str],
    tool_context: Optional[ToolContext],
    conversation_id: Optional[str],
    language: str,
    repository_name: str,
    repository_owner: str,
    repo_type: Optional[str],
) -> str:
    """Handle push to remote and finalization.

    Args:
        target_path: Repository path
        branch_name: Branch name
        use_existing_branch: Whether using existing branch
        user_repo_url: User repository URL
        installation_id: Installation ID
        tool_context: Tool context
        conversation_id: Conversation ID
        language: Programming language
        repository_name: Repository name
        repository_owner: Repository owner
        repo_type: Repository type

    Returns:
        Success message
    """
    from .finalization import _finalize_clone, _format_clone_success_message

    if not use_existing_branch and user_repo_url and installation_id:
        await _push_branch_to_remote(target_path, branch_name, user_repo_url)
    elif use_existing_branch:
        logger.info(f"ℹ️ Using existing branch - skipping push to remote")
    else:
        logger.warning("⚠️ No user repository URL or installation ID - skipping push")

    await _finalize_clone(
        tool_context, conversation_id, str(target_path), branch_name, language,
        repository_name, repository_owner, user_repo_url, installation_id, repo_type
    )

    logger.info(f"📦 Repository info: {repository_owner}/{repository_name}@{branch_name}")
    return _format_clone_success_message(
        use_existing_branch, repository_owner, repository_name, branch_name, str(target_path)
    )
