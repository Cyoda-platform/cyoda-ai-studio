"""Branch management operations for git.

This module contains functions for:
- Branch checkout (existing branches)
- Branch creation from base branch
- Branch existence checking
- Upstream tracking configuration
"""

import asyncio
import logging
import os
from typing import Optional

from common.config.config import CLIENT_GIT_BRANCH

logger = logging.getLogger(__name__)


async def checkout_branch_if_exists(
    clone_dir: str, git_branch_id: str
) -> Optional[str]:
    """Checkout existing branch.

    Args:
        clone_dir: Repository directory.
        git_branch_id: Branch ID to checkout.

    Returns:
        Error message if checkout failed, None if successful.
    """
    checkout_process = await asyncio.create_subprocess_exec(
        "git",
        "--git-dir",
        f"{clone_dir}/.git",
        "--work-tree",
        clone_dir,
        "checkout",
        str(git_branch_id),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await checkout_process.communicate()

    if checkout_process.returncode != 0:
        error_msg = f"Error during git checkout: {stderr.decode()}"
        logger.error(error_msg)
        return error_msg

    logger.info(f"Checked out existing branch: {git_branch_id}")
    return None


async def create_branch_from_base(
    clone_dir: str, git_branch_id: str, base_branch: Optional[str]
) -> Optional[str]:
    """Create new branch from base branch.

    Args:
        clone_dir: Repository directory.
        git_branch_id: New branch ID to create.
        base_branch: Base branch to create from.

    Returns:
        Error message if any step failed, None if successful.
    """
    base_branch = base_branch or CLIENT_GIT_BRANCH
    logger.info(f"Branch {git_branch_id} doesn't exist, creating from {base_branch}")

    # Checkout base branch first
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
    create_branch_process = await asyncio.create_subprocess_exec(
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
    stdout, stderr = await create_branch_process.communicate()

    if create_branch_process.returncode != 0:
        error_msg = f"Error during git checkout of new branch '{git_branch_id}': {stderr.decode()}"
        logger.error(error_msg)
        return error_msg

    # Set upstream tracking (requires being in the repo directory)
    original_dir = os.getcwd()
    try:
        os.chdir(clone_dir)
        await set_upstream_tracking(git_branch_id)
    finally:
        os.chdir(original_dir)

    logger.info(f"Created and checked out new branch: {git_branch_id}")
    return None


async def checkout_base_and_create_branch(
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


async def set_upstream_tracking(git_branch_id: str):
    """Set upstream tracking for branch.

    Args:
        git_branch_id: Branch ID
    """
    branch = git_branch_id
    process = await asyncio.create_subprocess_exec(
        "git",
        "branch",
        "--set-upstream-to",
        f"origin/{branch}",
        branch,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logger.error(f"Error setting upstream: {stderr.decode().strip()}")
    else:
        logger.info(f"Successfully set upstream tracking for branch {branch}.")


async def ensure_branch_exists(
    clone_dir: str, git_branch_id: str, base_branch: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """Ensure branch exists locally, creating if necessary.

    Checks if branch exists, then either checks it out or creates it from base branch.

    Args:
        clone_dir: Directory of the cloned repository.
        git_branch_id: Branch ID to ensure exists.
        base_branch: Base branch to create from if branch doesn't exist.

    Returns:
        Tuple of (success, error_message)
    """
    # Check if branch exists locally
    check_branch_process = await asyncio.create_subprocess_exec(
        "git",
        "--git-dir",
        f"{clone_dir}/.git",
        "--work-tree",
        clone_dir,
        "rev-parse",
        "--verify",
        str(git_branch_id),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await check_branch_process.communicate()

    if check_branch_process.returncode == 0:
        # Branch exists - checkout it
        error_msg = await checkout_branch_if_exists(clone_dir, git_branch_id)
        if error_msg:
            return False, error_msg
        return True, None

    # Branch doesn't exist - create it from base branch
    error_msg = await create_branch_from_base(clone_dir, git_branch_id, base_branch)
    if error_msg:
        return False, error_msg
    return True, None
