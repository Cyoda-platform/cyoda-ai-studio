"""Git clone operations module.

This module handles repository cloning functionality.
"""

import asyncio
import logging
import os
from typing import Optional

from application.services.github.auth.installation_token_manager import (
    InstallationTokenManager,
)
from application.services.github.models.types import GitOperationResult
from common.config.config import (
    CLIENT_GIT_BRANCH,
    CLONE_REPO,
    PROJECT_DIR,
)

logger = logging.getLogger(__name__)


async def _repo_exists(path: str) -> bool:
    """Check if path exists."""
    return await asyncio.to_thread(os.path.exists, path)


async def _perform_git_clone(repo_url: str, clone_dir: str) -> Optional[str]:
    """Perform git clone operation.

    Args:
        repo_url: Repository URL (possibly authenticated).
        clone_dir: Directory to clone into.

    Returns:
        Error message if clone failed, None if successful.
    """
    clone_process = await asyncio.create_subprocess_exec(
        "git",
        "clone",
        repo_url,
        clone_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await clone_process.communicate()

    if clone_process.returncode != 0:
        error_msg = f"Error during git clone: {stderr.decode()}"
        logger.error(error_msg)
        return error_msg

    return None


async def _checkout_base_and_create_branch(
    clone_dir: str, git_branch_id: str, base_branch: Optional[str]
) -> Optional[str]:
    """Checkout base branch and create new feature branch.

    Args:
        clone_dir: Repository directory.
        git_branch_id: New branch ID to create.
        base_branch: Base branch to checkout first.

    Returns:
        Error message if any step failed, None if successful.
    """
    base_branch = base_branch or CLIENT_GIT_BRANCH

    # Checkout base branch
    base_checkout_process = await asyncio.create_subprocess_exec(
        "git",
        "--git-dir",
        f"{clone_dir}/.git",
        "--work-tree",
        clone_dir,
        "checkout",
        base_branch,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await base_checkout_process.communicate()

    if base_checkout_process.returncode != 0:
        error_msg = f"Error during git checkout of base branch '{base_branch}': {stderr.decode()}"
        logger.error(error_msg)
        return error_msg

    # Create new branch
    checkout_process = await asyncio.create_subprocess_exec(
        "git",
        "--git-dir",
        f"{clone_dir}/.git",
        "--work-tree",
        clone_dir,
        "checkout",
        "-b",
        str(git_branch_id),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await checkout_process.communicate()

    if checkout_process.returncode != 0:
        error_msg = f"Error during git checkout of new branch '{git_branch_id}': {stderr.decode()}"
        logger.error(error_msg)
        return error_msg

    return None
