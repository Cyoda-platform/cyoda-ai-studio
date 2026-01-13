"""GitOperations class for managing local git command operations."""

import asyncio
import logging
import os
from typing import List, Optional

from application.services.github.auth.installation_token_manager import (
    InstallationTokenManager,
)
from application.services.github.models.types import GitOperationResult
from common.config.config import (
    CLIENT_GIT_BRANCH,
    CLONE_REPO,
    PROJECT_DIR,
)

from ..url_management import get_repository_url
from .helpers import (
    DEFAULT_MERGE_STRATEGY,
    NO_CHANGES_TO_PULL_MSG,
    build_branch_result,
    build_pull_result,
    build_push_result,
    get_clone_dir,
    should_skip_commit,
)
from .subprocess_execution import (
    add_files,
    check_repo_exists,
    checkout_and_create_branch,
    clone_repository,
    commit,
    configure_git,
    configure_merge_strategy,
    ensure_branch,
    fetch_from_remote,
    get_git_diff,
    pull_from_remote,
    push,
    set_branch_upstream_tracking,
)

logger = logging.getLogger(__name__)

_git_operations_lock = asyncio.Lock()


class GitOperations:
    """Handles all local git command operations with dual-mode authentication."""

    def __init__(self, installation_id: Optional[int] = None):
        """Initialize git operations.

        Args:
            installation_id: GitHub App installation ID (for private repos)
        """
        self._lock = _git_operations_lock
        self.installation_id = installation_id
        self._installation_token_manager = None

        if installation_id:
            self._installation_token_manager = InstallationTokenManager()
            logger.info(
                f"Git operations initialized with installation ID: {installation_id}"
            )

    async def _get_repository_url(
        self, repository_name: str, repository_url: Optional[str] = None
    ) -> str:
        """Get repository URL with authentication.

        Args:
            repository_name: Repository name (used for public repos)
            repository_url: Custom repository URL (used for private repos)

        Returns:
            Authenticated repository URL
        """
        return await get_repository_url(
            self.installation_id,
            self._installation_token_manager,
            repository_name,
            repository_url,
        )

    async def clone_repository(
        self,
        git_branch_id: str,
        repository_name: str,
        base_branch: Optional[str] = None,
        repository_url: Optional[str] = None,
    ) -> GitOperationResult:
        """Clone repository and create new feature branch.

        Clones repository, checks out base branch, and creates feature branch.
        Uses repository_name as directory name for consistency.

        Args:
            git_branch_id: Branch ID to create.
            repository_name: Repository name (used as directory name).
            base_branch: Base branch to checkout (defaults to CLIENT_GIT_BRANCH).
            repository_url: Custom repository URL (for private repos).

        Returns:
            GitOperationResult with success status and message.

        Note:
            repository_name must match config.JAVA_REPOSITORY_NAME or
            config.PYTHON_REPOSITORY_NAME for directory consistency.
        """
        async with self._lock:
            repo_url = await self._get_repository_url(repository_name, repository_url)
            clone_dir = f"{PROJECT_DIR}/{git_branch_id}/{repository_name}"
            base_branch = base_branch or CLIENT_GIT_BRANCH

            logger.info(f"Cloning repository to: {clone_dir}")

            # Return early if repository already exists
            if await check_repo_exists(clone_dir):
                await self._pull_internal(
                    git_branch_id, repository_name, repository_url
                )
                return GitOperationResult(
                    success=True,
                    message=f"Repository already exists at {clone_dir}, pulled latest changes",
                )

            # Handle CLONE_REPO=false case
            if not CLONE_REPO:
                await asyncio.to_thread(os.makedirs, clone_dir, exist_ok=True)
                logger.info(f"Target directory '{clone_dir}' is created.")
                return GitOperationResult(
                    success=True,
                    message=f"Directory created at {clone_dir} (CLONE_REPO=false)",
                )

            try:
                # Perform clone
                error_msg = await clone_repository(repo_url, clone_dir)
                if error_msg:
                    return GitOperationResult(
                        success=False, message="Clone failed", error=error_msg
                    )

                # Checkout base branch and create feature branch
                error_msg = await checkout_and_create_branch(
                    clone_dir, git_branch_id, base_branch
                )
                if error_msg:
                    return GitOperationResult(
                        success=False, message="Branch creation failed", error=error_msg
                    )

                logger.info(f"Repository cloned to {clone_dir}")

                # Setup git config and upstream tracking
                os.chdir(clone_dir)
                await set_branch_upstream_tracking(git_branch_id)
                await configure_git()
                await self._pull_internal(
                    git_branch_id, repository_name, repository_url
                )

                return GitOperationResult(
                    success=True,
                    message=f"Repository cloned successfully to {clone_dir}",
                )

            except Exception as e:
                error_msg = f"Unexpected error during clone: {e}"
                logger.error(error_msg)
                logger.exception(e)
                return GitOperationResult(
                    success=False, message="Clone failed", error=error_msg
                )

    async def pull(
        self,
        git_branch_id: str,
        repository_name: str,
        merge_strategy: str = "recursive",
        repository_url: Optional[str] = None,
    ) -> GitOperationResult:
        """Pull latest changes from remote.

        Args:
            git_branch_id: Branch ID
            repository_name: Repository name
            merge_strategy: Git merge strategy
            repository_url: Custom repository URL (for private repos)

        Returns:
            GitOperationResult with diff information
        """
        async with self._lock:
            return await self._pull_internal(
                git_branch_id, repository_name, repository_url, merge_strategy
            )

    async def _pull_internal(
        self,
        git_branch_id: str,
        repository_name: str,
        repository_url: Optional[str] = None,
        merge_strategy: str = DEFAULT_MERGE_STRATEGY,
    ) -> GitOperationResult:
        """Internal pull without lock.

        Args:
            git_branch_id: Branch ID
            repository_name: Repository name (used as directory name)
            repository_url: Custom repository URL (unused in this method)
            merge_strategy: Git merge strategy to use

        Returns:
            GitOperationResult with pull status and diff
        """
        try:
            # Step 1: Setup directory path
            clone_dir = get_clone_dir(git_branch_id, repository_name)

            # Step 2: Ensure branch exists (create if needed)
            success, error_msg = await ensure_branch(clone_dir, git_branch_id)
            if not success:
                return build_branch_result(success, error_msg, git_branch_id)

            # Step 3: Fetch latest changes from remote
            success, error_msg = await fetch_from_remote(clone_dir)
            if not success:
                return GitOperationResult(
                    success=False, message="Fetch failed", error=error_msg
                )

            # Step 4: Get diff between local and remote
            success, error_msg, diff_result = await get_git_diff(
                clone_dir, git_branch_id
            )
            if not success:
                return GitOperationResult(
                    success=False, message="Diff failed", error=error_msg
                )

            # Step 5: Check if there are changes to pull
            if not diff_result.strip():
                logger.info(NO_CHANGES_TO_PULL_MSG)
                return build_pull_result(had_changes=False, diff_result=diff_result)

            # Step 6: Configure pull strategy and execute pull
            await configure_merge_strategy(clone_dir)
            success, error_msg = await pull_from_remote(
                clone_dir, git_branch_id, merge_strategy
            )
            if not success:
                return GitOperationResult(
                    success=False, message="Pull failed", error=error_msg
                )

            # Step 7: Return success with changes
            return build_pull_result(had_changes=True, diff_result=diff_result)

        except Exception as e:
            error_msg = f"Unexpected error during git pull: {e}"
            logger.error(error_msg)
            logger.exception(e)
            return GitOperationResult(
                success=False, message="Pull failed", error=error_msg
            )

    async def push(
        self,
        git_branch_id: str,
        repository_name: str,
        file_paths: List[str],
        commit_message: str,
        repository_url: Optional[str] = None,
    ) -> GitOperationResult:
        """Push changes to remote repository.

        Pulls latest changes first, then adds files, commits, and pushes to branch.

        Args:
            git_branch_id: Branch ID.
            repository_name: Repository name.
            file_paths: List of file paths to add.
            commit_message: Commit message.
            repository_url: Custom repository URL (for private repos).

        Returns:
            GitOperationResult with success status.
        """
        async with self._lock:
            # Pull latest changes first
            pull_result = await self._pull_internal(
                git_branch_id, repository_name, repository_url
            )

            # Get clone directory
            clone_dir = get_clone_dir(git_branch_id, repository_name)

            try:
                # Add files to staging area
                error_msg = await add_files(clone_dir, file_paths)
                if error_msg:
                    return build_push_result(False, "Add failed", error_msg)

                # Commit staged changes
                error_msg = await commit(clone_dir, commit_message, git_branch_id)
                if should_skip_commit(error_msg):
                    logger.info("No changes to commit - files are already up to date")
                    return build_push_result(True, "No changes to commit")
                if error_msg:
                    return build_push_result(False, "Commit failed", error_msg)

                # Push to remote
                error_msg = await push(clone_dir, git_branch_id)
                if error_msg:
                    return build_push_result(False, "Push failed", error_msg)

                return build_push_result(True, "Push successful")

            except Exception as e:
                error_msg = f"Unexpected error during git push: {e}"
                logger.error(error_msg)
                logger.exception(e)
                return GitOperationResult(
                    success=False, message="Push failed", error=error_msg
                )

    async def _repo_exists(self, clone_dir: str) -> bool:
        """Check if repository exists at path (for test compatibility).

        Args:
            clone_dir: Directory path to check

        Returns:
            True if repository exists
        """
        return await check_repo_exists(clone_dir)

    async def _set_upstream_tracking(self, branch_name: str) -> None:
        """Set upstream tracking for branch (for test compatibility).

        Args:
            branch_name: Branch name to set upstream for
        """
        await set_branch_upstream_tracking(branch_name)

    async def _run_git_config(self) -> None:
        """Run git config (for test compatibility)."""
        await configure_git()

    async def _ensure_branch_exists(
        self, clone_dir: str, git_branch_id: str
    ) -> tuple[bool, Optional[str]]:
        """Ensure branch exists (for test compatibility).

        Args:
            clone_dir: Clone directory path
            git_branch_id: Branch ID

        Returns:
            Tuple of (success, error_message)
        """
        return await ensure_branch(clone_dir, git_branch_id)

    async def repository_exists(self, git_branch_id: str, repository_name: str) -> bool:
        """Check if repository directory exists.

        Args:
            git_branch_id: Branch ID
            repository_name: Repository name

        Returns:
            True if repository exists
        """
        path = f"{PROJECT_DIR}/{git_branch_id}/{repository_name}"
        return await check_repo_exists(path)
