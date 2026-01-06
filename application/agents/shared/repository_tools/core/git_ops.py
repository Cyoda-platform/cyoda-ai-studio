"""Git operations for repository management."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def _clone_repo_to_path(repo_url: str, target_path: Path) -> tuple[bool, Optional[str]]:
    """Clone repository to target path.

    Args:
        repo_url: Repository URL to clone
        target_path: Target directory path

    Returns:
        Tuple of (success, error_message)
    """
    # Import here to allow test mocking via repository module
    from application.agents.shared.repository_tools import repository

    clone_cmd = ["git", "clone", repo_url, str(target_path)]
    returncode, stdout, stderr = await repository._run_git_command(clone_cmd, timeout=300)

    if returncode != 0:
        error_msg = stderr or stdout
        logger.error(f"Git clone failed: {error_msg}")
        return False, error_msg

    return True, None


async def _checkout_existing_branch(
    target_path: Path,
    branch_name: str
) -> tuple[bool, Optional[str]]:
    """Checkout and pull existing branch.

    Args:
        target_path: Repository path
        branch_name: Branch name to checkout

    Returns:
        Tuple of (success, error_message)
    """
    # Import here to allow test mocking via repository module
    from application.agents.shared.repository_tools import repository

    # Fetch all branches from remote
    fetch_cmd = ["git", "fetch", "origin"]
    returncode, stdout, stderr = await repository._run_git_command(
        fetch_cmd,
        cwd=str(target_path),
        timeout=300,
    )

    if returncode != 0:
        logger.warning(f"Failed to fetch from remote: {stderr or stdout}")

    # Checkout the existing branch
    checkout_cmd = ["git", "checkout", branch_name]
    returncode, stdout, stderr = await repository._run_git_command(
        checkout_cmd,
        cwd=str(target_path),
        timeout=30,
    )

    if returncode != 0:
        error_msg = stderr or stdout
        logger.error(f"Failed to checkout existing branch '{branch_name}': {error_msg}")
        return False, error_msg

    # Configure git pull strategy to merge
    config_cmd = ["git", "config", "pull.rebase", "false"]
    returncode, stdout, stderr = await repository._run_git_command(
        config_cmd,
        cwd=str(target_path),
        timeout=30,
    )

    if returncode != 0:
        logger.warning(f"Failed to set git pull.rebase config: {stderr or stdout}")
    else:
        logger.info("Git pull.rebase set to false (merge strategy)")

    # Pull latest changes from remote
    pull_cmd = ["git", "pull", "origin", branch_name]
    returncode, stdout, stderr = await repository._run_git_command(
        pull_cmd,
        cwd=str(target_path),
        timeout=300,
    )

    if returncode != 0:
        logger.warning(f"Failed to pull latest changes: {stderr or stdout}")

    logger.info(f"✅ Successfully checked out existing branch '{branch_name}'")
    return True, None


async def _create_new_branch(
    target_path: Path,
    branch_name: str,
    base_branch: str
) -> bool:
    """Create and checkout new branch.

    Args:
        target_path: Repository path
        branch_name: New branch name
        base_branch: Base branch to create from

    Returns:
        True if successful
    """
    # Import here to allow test mocking via repository module
    from application.agents.shared.repository_tools import repository

    # Checkout base branch first
    checkout_base_cmd = ["git", "checkout", base_branch]
    returncode, stdout, stderr = await repository._run_git_command(
        checkout_base_cmd,
        cwd=str(target_path),
        timeout=30,
    )

    if returncode != 0:
        logger.warning(f"Failed to checkout base branch '{base_branch}': {stderr or stdout}")

    # Create and checkout new branch
    checkout_cmd = ["git", "checkout", "-b", branch_name]
    returncode, stdout, stderr = await repository._run_git_command(
        checkout_cmd,
        cwd=str(target_path),
        timeout=30,
    )

    if returncode != 0:
        logger.warning(f"Failed to create branch {branch_name}: {stderr or stdout}")
        # Try to checkout existing branch
        checkout_cmd = ["git", "checkout", branch_name]
        await repository._run_git_command(
            checkout_cmd,
            cwd=str(target_path),
            timeout=30,
        )

    return True


async def _push_branch_to_remote(
    target_path: Path,
    branch_name: str,
    repo_url: Optional[str]
) -> None:
    """Push new branch to remote repository.

    Args:
        target_path: Repository path
        branch_name: Branch name to push
        repo_url: Remote repository URL (for logging)
    """
    # Import here to allow test mocking via repository module
    from application.agents.shared.repository_tools import repository

    logger.info(f"🚀 Pushing new branch {branch_name} to {repo_url}...")
    push_cmd = ["git", "push", "--set-upstream", "origin", branch_name]
    returncode, stdout, stderr = await repository._run_git_command(
        push_cmd,
        cwd=str(target_path),
        timeout=300,
    )

    if returncode != 0:
        logger.warning(f"⚠️ Failed to push branch {branch_name} to remote: {stderr or stdout}")
    else:
        logger.info(f"✅ Successfully pushed branch {branch_name} to {repo_url}")
