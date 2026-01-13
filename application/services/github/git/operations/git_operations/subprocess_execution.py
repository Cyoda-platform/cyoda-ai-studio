"""Subprocess execution wrappers for git operations."""

import logging
from typing import List, Optional

from ..branch_management import (
    checkout_base_and_create_branch,
    checkout_branch_if_exists,
    create_branch_from_base,
    ensure_branch_exists,
    set_upstream_tracking,
)
from ..local_operations import (
    add_files_to_git,
    commit_changes,
    configure_pull_strategy,
    perform_git_clone,
    push_to_remote,
    repo_exists,
    run_git_config,
    run_git_diff,
    run_git_fetch,
    run_git_pull,
)

logger = logging.getLogger(__name__)


async def check_repo_exists(path: str) -> bool:
    """Check if path exists."""
    return await repo_exists(path)


async def configure_git():
    """Configure git pull behavior."""
    await run_git_config()


async def set_branch_upstream_tracking(git_branch_id: str):
    """Set upstream tracking for branch."""
    await set_upstream_tracking(git_branch_id)


async def ensure_branch(
    clone_dir: str, git_branch_id: str, base_branch: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """Ensure branch exists locally, creating if necessary."""
    return await ensure_branch_exists(clone_dir, git_branch_id, base_branch)


async def fetch_from_remote(clone_dir: str) -> tuple[bool, Optional[str]]:
    """Fetch latest changes from remote."""
    return await run_git_fetch(clone_dir)


async def get_git_diff(
    clone_dir: str, git_branch_id: str
) -> tuple[bool, Optional[str], Optional[str]]:
    """Get diff between local and remote branch."""
    return await run_git_diff(clone_dir, git_branch_id)


async def configure_merge_strategy(clone_dir: str) -> bool:
    """Configure git pull to use merge strategy."""
    return await configure_pull_strategy(clone_dir)


async def pull_from_remote(
    clone_dir: str, git_branch_id: str, merge_strategy: str
) -> tuple[bool, Optional[str]]:
    """Execute git pull with specified merge strategy."""
    return await run_git_pull(clone_dir, git_branch_id, merge_strategy)


async def add_files(clone_dir: str, file_paths: List[str]) -> Optional[str]:
    """Add files to git staging area."""
    return await add_files_to_git(clone_dir, file_paths)


async def commit(
    clone_dir: str, commit_message: str, git_branch_id: str
) -> Optional[str]:
    """Commit staged changes to git."""
    return await commit_changes(clone_dir, commit_message, git_branch_id)


async def push(clone_dir: str, git_branch_id: str) -> Optional[str]:
    """Push changes to remote repository."""
    return await push_to_remote(clone_dir, git_branch_id)


async def checkout_branch(clone_dir: str, git_branch_id: str) -> Optional[str]:
    """Checkout existing branch."""
    return await checkout_branch_if_exists(clone_dir, git_branch_id)


async def create_branch(
    clone_dir: str, git_branch_id: str, base_branch: Optional[str]
) -> Optional[str]:
    """Create new branch from base branch."""
    return await create_branch_from_base(clone_dir, git_branch_id, base_branch)


async def clone_repository(repo_url: str, clone_dir: str) -> Optional[str]:
    """Perform git clone operation."""
    return await perform_git_clone(repo_url, clone_dir)


async def checkout_and_create_branch(
    clone_dir: str, git_branch_id: str, base_branch: Optional[str]
) -> Optional[str]:
    """Checkout base branch and create new feature branch."""
    return await checkout_base_and_create_branch(clone_dir, git_branch_id, base_branch)
