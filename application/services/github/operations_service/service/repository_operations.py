"""Repository cloning and checkout operations."""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..auth import get_authenticated_clone_url
from ..helpers import (
    determine_repository_path,
    extract_repository_name_from_url,
    verify_repository_exists,
)
from .subprocess_helpers import (
    CHECKOUT_TIMEOUT_SECONDS,
    CLONE_TIMEOUT_SECONDS,
    run_subprocess,
)

logger = logging.getLogger(__name__)


async def clone_repository_from_url(
    clone_url: str,
    repo_path_obj: Path,
    original_url: str,
) -> bool:
    """Clone repository from remote URL.

    Args:
        clone_url: Authenticated or public clone URL.
        repo_path_obj: Local path to clone into.
        original_url: Original repository URL (for logging).

    Returns:
        True if clone succeeded.
    """
    logger.info(f"🔄 Cloning repository from {original_url}...")
    result = await run_subprocess(
        ["git", "clone", clone_url, str(repo_path_obj)], timeout=CLONE_TIMEOUT_SECONDS
    )
    if result["returncode"] != 0:
        error_msg = result["stderr"] or result["stdout"]
        logger.error(f"❌ Clone failed: {error_msg}")
        return False
    return True


async def checkout_branch(
    repo_path_obj: Path,
    branch_name: str,
) -> Tuple[bool, Optional[str]]:
    """Checkout git branch, fetching if necessary.

    Args:
        repo_path_obj: Path to repository.
        branch_name: Git branch name to checkout.

    Returns:
        Tuple of (success, error_message). Error is None if successful.
    """
    logger.info(f"🔄 Checking out branch {branch_name}...")
    checkout_res = await run_subprocess(
        ["git", "checkout", branch_name],
        cwd=str(repo_path_obj),
        timeout=CHECKOUT_TIMEOUT_SECONDS,
    )

    if checkout_res["returncode"] == 0:
        return True, None

    # Try fetch and retry checkout
    logger.warning(f"Branch {branch_name} not found locally, fetching...")
    await run_subprocess(
        ["git", "fetch", "origin"],
        cwd=str(repo_path_obj),
        timeout=CLONE_TIMEOUT_SECONDS,
    )

    # Retry checkout
    checkout_res = await run_subprocess(
        ["git", "checkout", branch_name],
        cwd=str(repo_path_obj),
        timeout=CHECKOUT_TIMEOUT_SECONDS,
    )

    if checkout_res["returncode"] != 0:
        error_msg = f"Failed to checkout branch {branch_name}: {checkout_res['stderr']}"
        logger.error(f"❌ {error_msg}")
        return False, error_msg

    return True, None


async def ensure_repository_cloned(
    repository_url: str,
    repository_branch: str,
    installation_id: Optional[str] = None,
    repository_name: Optional[str] = None,
    use_env_installation_id: bool = True,
) -> Tuple[bool, str, Optional[str]]:
    """Ensure repository is cloned locally, cloning if necessary.

    Retrieves repository from GitHub, handling authentication and branch
    checkout. Returns early if repository already exists locally.

    Args:
        repository_url: GitHub repository URL.
        repository_branch: Git branch name to checkout.
        installation_id: GitHub installation ID (optional).
        repository_name: Repository name (extracted from URL if not provided).
        use_env_installation_id: Whether to use environment installation ID.

    Returns:
        Tuple of (success, message, repository_path).
    """
    try:
        # Extract repository name if not provided
        if not repository_name:
            repository_name, error = extract_repository_name_from_url(repository_url)
            if error:
                return False, error, None

        # Determine repository path
        repo_path_obj = determine_repository_path(repository_branch)
        repository_path = str(repo_path_obj)

        # Return early if already cloned
        if verify_repository_exists(repo_path_obj):
            logger.info(f"✅ Repository already cloned at {repository_path}")
            return (
                True,
                f"Repository already exists at {repository_path}",
                repository_path,
            )

        logger.info(
            f"📦 Repository not found at {repository_path}, cloning from {repository_url}"
        )

        # Get authenticated clone URL
        clone_url = await get_authenticated_clone_url(
            repository_url,
            installation_id,
            use_env_installation_id,
        )

        # Create directory and clone
        repo_path_obj.mkdir(parents=True, exist_ok=True)
        success = await clone_repository_from_url(
            clone_url, repo_path_obj, repository_url
        )
        if not success:
            return False, f"Failed to clone repository: {repository_url}", None

        # Checkout branch
        success, error_msg = await checkout_branch(repo_path_obj, repository_branch)
        if not success:
            return False, error_msg, None

        logger.info(f"✅ Repository cloned successfully at {repository_path}")
        return (
            True,
            f"Repository cloned successfully at {repository_path}",
            repository_path,
        )

    except Exception as e:
        logger.error(f"❌ Error ensuring repository is cloned: {e}", exc_info=True)
        return False, f"Error cloning repository: {str(e)}", None


async def pull_changes(repository_path: str, branch_name: str) -> str:
    """Pull latest changes.

    Args:
        repository_path: Path to repository
        branch_name: Branch name to pull

    Returns:
        Standard output from git pull

    Raises:
        Exception: If pull fails
    """
    res = await run_subprocess(
        ["git", "pull", "origin", branch_name], cwd=repository_path
    )
    if res["returncode"] != 0:
        raise Exception(f"Git pull failed: {res['stderr']}")
    return res["stdout"]


async def get_repository_diff(repository_path: str) -> Dict[str, list]:
    """Get diff of uncommitted changes.

    Args:
        repository_path: Path to repository

    Returns:
        Dictionary with modified, added, deleted, untracked file lists

    Raises:
        Exception: If diff operation fails
    """
    try:
        result = await run_subprocess(
            ["git", "status", "--porcelain"], cwd=repository_path
        )

        changes: Dict[str, list] = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        for line in result["stdout"].strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            file_path = line[3:]
            if status.strip() == "M":
                changes["modified"].append(file_path)
            elif status.strip() == "A":
                changes["added"].append(file_path)
            elif status.strip() == "D":
                changes["deleted"].append(file_path)
            elif status.strip() == "??":
                changes["untracked"].append(file_path)

        return changes
    except Exception as e:
        logger.error(f"Error getting repository diff: {e}")
        raise
