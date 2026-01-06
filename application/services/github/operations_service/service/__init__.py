"""GitHub operations service - Re-exports for backward compatibility."""

from .repository_operations import (
    clone_repository_from_url,
    checkout_branch,
    ensure_repository_cloned,
    pull_changes,
    get_repository_diff,
)
from .commit_operations import (
    extract_changed_files,
    configure_git_user,
    stage_all_changes,
    perform_commit,
    refresh_authentication,
    push_with_retry,
    detect_canvas_resources,
    commit_and_push,
)
from .subprocess_helpers import (
    run_subprocess,
    run_git_cmd,
    CLONE_TIMEOUT_SECONDS,
    CHECKOUT_TIMEOUT_SECONDS,
)

# Import service class from parent to maintain compatibility
import sys
import os

# Add current directory to path temporarily
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Define GitHubOperationsService class
class GitHubOperationsService:
    """Service for handling git operations."""

    def __init__(self):
        pass

    async def ensure_repository(
        self,
        repository_url: str,
        repository_branch: str,
        installation_id: str | None = None,
        repository_name: str | None = None,
        use_env_installation_id: bool = True,
    ):
        """Ensure repository is cloned locally."""
        return await ensure_repository_cloned(
            repository_url,
            repository_branch,
            installation_id,
            repository_name,
            use_env_installation_id,
        )

    async def get_repository_diff(self, repository_path: str):
        """Get diff of uncommitted changes."""
        return await get_repository_diff(repository_path)

    async def commit_and_push(
        self,
        repository_path: str,
        commit_message: str,
        branch_name: str,
        repo_auth_config: dict,
    ):
        """Commit and push changes to repository."""
        return await commit_and_push(
            repository_path, commit_message, branch_name, repo_auth_config
        )

    async def pull_changes(self, repository_path: str, branch_name: str):
        """Pull latest changes."""
        return await pull_changes(repository_path, branch_name)

    async def _run_subprocess(self, cmd, cwd=None, timeout=None, check=False):
        """Run subprocess safely."""
        return await run_subprocess(cmd, cwd, timeout, check)

    async def _run_git_cmd(self, args, check=True):
        """Helper to run git commands."""
        return await run_git_cmd(args, check)

    # Legacy private methods for compatibility
    async def _clone_repository(self, clone_url, repo_path_obj, original_url):
        """Clone repository from remote URL."""
        return await clone_repository_from_url(clone_url, repo_path_obj, original_url)

    async def _checkout_branch(self, repo_path_obj, branch_name):
        """Checkout git branch."""
        return await checkout_branch(repo_path_obj, branch_name)

    async def _extract_changed_files(self):
        """Extract list of changed files."""
        return await extract_changed_files()

    async def _configure_git_user(self):
        """Configure git user."""
        await configure_git_user()

    async def _stage_all_changes(self):
        """Stage all changes."""
        await stage_all_changes()

    async def _perform_commit(self, commit_message):
        """Perform git commit."""
        return await perform_commit(commit_message)

    async def _refresh_authentication(self, repo_auth_config):
        """Refresh authentication."""
        await refresh_authentication(repo_auth_config)

    async def _push_with_retry(self, branch_name, max_attempts=2):
        """Push with retry."""
        await push_with_retry(branch_name, max_attempts)

    async def _detect_canvas_resources(self, changed_files):
        """Detect canvas resources."""
        return await detect_canvas_resources(changed_files)


__all__ = [
    "GitHubOperationsService",
    "clone_repository_from_url",
    "checkout_branch",
    "ensure_repository_cloned",
    "pull_changes",
    "get_repository_diff",
    "extract_changed_files",
    "configure_git_user",
    "stage_all_changes",
    "perform_commit",
    "refresh_authentication",
    "push_with_retry",
    "detect_canvas_resources",
    "commit_and_push",
    "run_subprocess",
    "run_git_cmd",
    "CLONE_TIMEOUT_SECONDS",
    "CHECKOUT_TIMEOUT_SECONDS",
]
