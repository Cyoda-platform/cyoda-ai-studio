"""Branch handling operations for repository setup.

This module handles creating new branches and checking out existing branches
during repository clone operations.
"""

import logging
from pathlib import Path
from typing import Optional

from ..git_ops import _checkout_existing_branch, _create_new_branch

logger = logging.getLogger(__name__)


async def _handle_new_branch(
    target_path: Path, base_branch: str, branch_name: str, user_repo_url: Optional[str]
) -> tuple[bool, Optional[str]]:
    """Create new branch and return success status.

    Args:
        target_path: Repository path
        base_branch: Base branch name
        branch_name: New branch name
        user_repo_url: User's repository URL

    Returns:
        Tuple of (success, error_message)
    """
    logger.info(f"🔄 Creating new branch '{branch_name}' from '{base_branch}'...")
    await _create_new_branch(target_path, branch_name, base_branch)
    return True, None


async def _handle_existing_branch(
    target_path: Path, branch_name: str
) -> tuple[bool, Optional[str]]:
    """Checkout existing branch and return success status.

    Args:
        target_path: Repository path
        branch_name: Branch name

    Returns:
        Tuple of (success, error_message)
    """
    logger.info(f"🔄 Checking out existing branch '{branch_name}' from remote...")
    success, error_msg = await _checkout_existing_branch(target_path, branch_name)
    if not success:
        error_msg = (
            f"ERROR: Branch '{branch_name}' does not exist in the repository. "
            f"Please verify the branch name. Error: {error_msg}"
        )
    return success, error_msg


async def _handle_branch_setup(
    target_path: Path,
    branch_name: str,
    use_existing_branch: bool,
    user_repo_url: Optional[str],
) -> Optional[str]:
    """Setup branch (create new or checkout existing).

    Args:
        target_path: Repository path
        branch_name: Branch name
        use_existing_branch: Whether to use existing branch
        user_repo_url: User repository URL

    Returns:
        Error message if failed, None if successful
    """
    from common.config.config import CLIENT_GIT_BRANCH

    base_branch = CLIENT_GIT_BRANCH

    if use_existing_branch:
        success, error_msg = await _handle_existing_branch(target_path, branch_name)
        if not success:
            return error_msg
    else:
        await _handle_new_branch(target_path, base_branch, branch_name, user_repo_url)

    return None
