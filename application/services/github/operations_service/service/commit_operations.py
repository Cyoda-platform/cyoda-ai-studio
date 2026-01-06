"""Commit and push operations for GitHub repositories."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .subprocess_helpers import run_git_cmd

logger = logging.getLogger(__name__)


async def extract_changed_files() -> List[str]:
    """Extract list of changed files from git status.

    Returns:
        List of changed file paths.
    """
    changed_files = []
    status_res = await run_git_cmd(["status", "--porcelain"])
    if status_res["returncode"] == 0:
        for line in status_res["stdout"].splitlines():
            if len(line) > 3:
                changed_files.append(line[3:].strip())
    return changed_files


async def configure_git_user() -> None:
    """Configure git user for commit operations."""
    await run_git_cmd(["config", "user.name", "Cyoda Agent"])
    await run_git_cmd(["config", "user.email", "agent@cyoda.ai"])


async def stage_all_changes() -> None:
    """Stage all changes for commit."""
    await run_git_cmd(["add", "."])


async def perform_commit(commit_message: str) -> Tuple[bool, Optional[str]]:
    """Perform git commit operation.

    Args:
        commit_message: Commit message.

    Returns:
        Tuple of (success, error_message). Error is None if successful.
    """
    commit_res = await run_git_cmd(["commit", "-m", commit_message], check=False)
    if commit_res["returncode"] != 0:
        output = commit_res["stdout"] + commit_res["stderr"]
        if "nothing to commit" in output.lower() or "working tree clean" in output.lower():
            return False, "nothing_to_commit"
        return False, output
    return True, None


async def refresh_authentication(repo_auth_config: Dict[str, Any]) -> None:
    """Refresh authentication token before push.

    Args:
        repo_auth_config: Repository authentication configuration.
    """
    if not repo_auth_config.get("url"):
        return

    try:
        from common.config.config import GITHUB_PUBLIC_REPO_INSTALLATION_ID

        inst_id = repo_auth_config.get("installation_id")
        if not inst_id and repo_auth_config.get("type") == "public":
            inst_id = GITHUB_PUBLIC_REPO_INSTALLATION_ID

        if inst_id:
            from application.agents.shared.repository_tools import (
                _get_authenticated_repo_url_sync,
            )

            auth_url = await _get_authenticated_repo_url_sync(
                repo_auth_config["url"], inst_id
            )
            await run_git_cmd(["remote", "set-url", "origin", auth_url])
            logger.debug("🔐 Refreshed authentication token before push")
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to refresh auth token, attempting push anyway: {e}"
        )


async def push_with_retry(branch_name: str, max_attempts: int = 2) -> None:
    """Push changes to remote with retry logic.

    Args:
        branch_name: Git branch name to push to.
        max_attempts: Maximum push attempts.

    Raises:
        Exception: If all push attempts fail.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            await run_git_cmd(["push", "origin", branch_name])
            logger.debug(f"✅ Push successful on attempt {attempt}")
            return
        except Exception as error:
            if attempt < max_attempts:
                logger.warning(
                    f"⚠️ Push attempt {attempt} failed, retrying: {error}"
                )
                await asyncio.sleep(2)
            else:
                logger.error(f"❌ Push failed after {max_attempts} attempts")
                raise


async def detect_canvas_resources(changed_files: List[str]) -> Dict[str, Any]:
    """Detect canvas resources from changed files.

    Args:
        changed_files: List of changed file paths.

    Returns:
        Dictionary of detected canvas resources.
    """
    from application.agents.shared.hooks import detect_canvas_resources

    return detect_canvas_resources(changed_files)


async def commit_and_push(
    repository_path: str,
    commit_message: str,
    branch_name: str,
    repo_auth_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Commit and push changes to repository.

    Stages all changes, commits with provided message, refreshes authentication,
    and pushes to remote with retry logic. Returns early if nothing to commit.

    Args:
        repository_path: Path to repository.
        commit_message: Git commit message.
        branch_name: Git branch name.
        repo_auth_config: Repository authentication configuration.

    Returns:
        Dictionary with success status, changed files, and canvas resources.

    Raises:
        Exception: If commit or push operations fail.
    """
    original_cwd = os.getcwd()

    try:
        os.chdir(repository_path)

        # Extract changed files
        changed_files = await extract_changed_files()

        # Configure git user
        await configure_git_user()

        # Stage changes
        await stage_all_changes()

        # Perform commit
        success, error = await perform_commit(commit_message)
        if not success:
            if error == "nothing_to_commit":
                return {
                    "success": True,
                    "message": "No changes to commit",
                    "changed_files": [],
                }
            raise Exception(f"Commit failed: {error}")

        # Refresh authentication
        await refresh_authentication(repo_auth_config)

        # Push with retry
        await push_with_retry(branch_name)

        # Detect canvas resources
        canvas_resources = await detect_canvas_resources(changed_files)

        return {
            "success": True,
            "changed_files": changed_files,
            "canvas_resources": canvas_resources,
        }

    except Exception as e:
        logger.error(f"Error in commit_and_push: {e}")
        raise
    finally:
        os.chdir(original_cwd)
