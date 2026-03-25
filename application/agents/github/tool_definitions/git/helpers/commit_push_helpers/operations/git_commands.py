"""Individual git command operations.

This module provides functions for executing individual git commands:
staging, committing, pushing, and configuration.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from application.agents.github.tool_definitions.common.constants import (
    GIT_ADD,
    GIT_ALL_FILES,
    GIT_CMD,
    GIT_COMMIT,
    GIT_COMMIT_MESSAGE_FLAG,
    GIT_CONFIG,
    GIT_DEFAULT_USER_EMAIL,
    GIT_DEFAULT_USER_NAME,
    GIT_GET_URL,
    GIT_ORIGIN,
    GIT_PUSH,
    GIT_REMOTE,
)

logger = logging.getLogger(__name__)

# Get the project root directory (where the tests folder is)
PROJECT_ROOT = Path(__file__).resolve().parents[8]  # Go up to project root


def _is_test_mode_with_real_repo(repo_path: str) -> bool:
    """Check if we're running tests and repo_path points to the actual project directory.

    This prevents tests from accidentally committing to the real repository.

    Args:
        repo_path: Path to check

    Returns:
        True if in test mode and using real project directory
    """
    # Check if running under pytest or adk eval
    in_test = (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in os.environ.get("_", "")
        or "adk" in os.environ.get("_", "")
    )

    if not in_test:
        return False

    # Check if repo_path is the actual project directory
    try:
        repo_path_obj = Path(repo_path).resolve()
        project_root_resolved = PROJECT_ROOT.resolve()

        # Check if paths are the same or repo_path is within project root
        is_project_dir = repo_path_obj == project_root_resolved or str(
            repo_path_obj
        ).startswith(str(project_root_resolved))

        # Also check if repo_path contains a tests/ directory (strong indicator it's the project root)
        has_tests_dir = (repo_path_obj / "tests").exists()

        return is_project_dir and has_tests_dir
    except Exception:
        return False


async def _stage_all_changes(repository_path: str) -> bool:
    """Stage all changes in repository.

    Args:
        repository_path: Path to repository

    Returns:
        True if successful, False otherwise
    """
    logger.info("📝 Running: git add .")
    process = await asyncio.create_subprocess_exec(
        GIT_CMD,
        GIT_ADD,
        GIT_ALL_FILES,
        cwd=repository_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    add_stdout, add_stderr = await process.communicate()
    logger.info(f"📝 git add returncode: {process.returncode}")

    if add_stderr:
        logger.info(
            f"📝 git add stderr: {add_stderr.decode('utf-8', errors='replace')}"
        )

    return process.returncode == 0


async def _configure_git_user(repository_path: str) -> bool:
    """Configure git user for repository.

    Args:
        repository_path: Path to repository

    Returns:
        True if successful, False otherwise
    """
    logger.info("🔧 Configuring git user for repository...")

    # Set git user.name
    config_name_process = await asyncio.create_subprocess_exec(
        GIT_CMD,
        GIT_CONFIG,
        "user.name",
        GIT_DEFAULT_USER_NAME,
        cwd=repository_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await config_name_process.communicate()

    # Set git user.email
    config_email_process = await asyncio.create_subprocess_exec(
        GIT_CMD,
        GIT_CONFIG,
        "user.email",
        GIT_DEFAULT_USER_EMAIL,
        cwd=repository_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await config_email_process.communicate()

    logger.info("✅ Git user configured")
    return True


async def _commit_changes(repository_path: str, branch_name: str) -> bool:
    """Commit staged changes.

    Args:
        repository_path: Path to repository
        branch_name: Branch name for commit message

    Returns:
        True if successful, False otherwise
    """
    # SAFETY CHECK: Prevent tests/evals from committing to the real project repository
    if _is_test_mode_with_real_repo(repository_path):
        error_msg = (
            "🚨 SAFETY CHECK FAILED: Attempted to commit to actual project directory during tests/evals. "
            f"Repository path: {repository_path}. Tests must use temporary directories for git operations."
        )
        logger.error(error_msg)
        return False

    commit_msg = f"Code generation progress on {branch_name}"
    logger.info(f"📝 Running: git commit -m '{commit_msg}'")

    process = await asyncio.create_subprocess_exec(
        GIT_CMD,
        GIT_COMMIT,
        GIT_COMMIT_MESSAGE_FLAG,
        commit_msg,
        cwd=repository_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    commit_stdout, commit_stderr = await process.communicate()
    logger.info(f"📝 git commit returncode: {process.returncode}")

    if commit_stderr:
        logger.info(
            f"📝 git commit stderr: {commit_stderr.decode('utf-8', errors='replace')}"
        )

    return process.returncode == 0


async def _get_current_remote_url(repository_path: str) -> str:
    """Get current git remote URL.

    Args:
        repository_path: Path to repository

    Returns:
        Current remote URL
    """
    logger.info("📝 Checking current git remote URL...")
    remote_process = await asyncio.create_subprocess_exec(
        GIT_CMD,
        GIT_REMOTE,
        GIT_GET_URL,
        GIT_ORIGIN,
        cwd=repository_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    remote_stdout, remote_stderr = await remote_process.communicate()
    current_remote_url = remote_stdout.decode("utf-8", errors="replace").strip()
    logger.info(f"🔐 Current git remote URL: {current_remote_url}")
    return current_remote_url


async def _push_changes(repository_path: str, branch_name: str) -> tuple[bool, str]:
    """Push changes to remote.

    Args:
        repository_path: Path to repository
        branch_name: Branch name

    Returns:
        Tuple of (success, error_message)
    """
    logger.info(f"📝 Running: git push origin {branch_name}")
    push_process = await asyncio.create_subprocess_exec(
        GIT_CMD,
        GIT_PUSH,
        GIT_ORIGIN,
        branch_name,
        cwd=repository_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await push_process.communicate()
    logger.info(f"📝 git push returncode: {push_process.returncode}")
    logger.info(f"📝 git push stdout: {stdout.decode('utf-8', errors='replace')}")
    logger.info(f"📝 git push stderr: {stderr.decode('utf-8', errors='replace')}")

    if push_process.returncode == 0:
        return True, ""

    error_msg = stderr.decode("utf-8", errors="replace")
    return False, error_msg
