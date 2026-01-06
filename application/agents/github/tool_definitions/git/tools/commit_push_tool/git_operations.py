"""Git operations for commit and push functionality."""

from __future__ import annotations

import asyncio
import logging
from typing import Tuple

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import STOP_ON_ERROR
from .context import GitConfiguration

logger = logging.getLogger(__name__)

# Git configuration constants
GIT_CONFIG_NAME_LOG = "🔧 Configuring git user for repository..."
GIT_CONFIG_SUCCESS_LOG = "✅ Git user configured"
GIT_ADD_FAILURE_LOG = "Git add failed: {error}"
GIT_ADD_FAILURE_ERROR = "ERROR: Failed to add files: {error}{stop}"
GIT_COMMIT_FAILURE_LOG = "Git commit failed: stdout={stdout}, stderr={stderr}"
GIT_COMMIT_FAILURE_ERROR = "ERROR: Failed to commit: {error}{stop}"
GIT_NOTHING_TO_COMMIT = (
    "SUCCESS: No changes to commit. The file was already saved and committed previously. "
    "Task complete - STOP, do not call any more tools."
)
GIT_NOTHING_TO_COMMIT_PATTERN1 = "nothing to commit"
GIT_NOTHING_TO_COMMIT_PATTERN2 = "working tree clean"


async def _configure_git_user(
    repository_path: str, config: GitConfiguration
) -> Tuple[bool, str]:
    """Configure git user name and email.

    Args:
        repository_path: Path to repository
        config: Git configuration

    Returns:
        Tuple of (success, error_message)
    """
    logger.info(GIT_CONFIG_NAME_LOG)

    # Configure user name
    name_process = await asyncio.create_subprocess_exec(
        'git', 'config', 'user.name', config.user_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repository_path
    )
    await name_process.communicate()

    # Configure user email
    email_process = await asyncio.create_subprocess_exec(
        'git', 'config', 'user.email', config.user_email,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repository_path
    )
    await email_process.communicate()

    logger.info(GIT_CONFIG_SUCCESS_LOG)
    return True, ""


async def _stage_all_changes(repository_path: str) -> Tuple[bool, str]:
    """Stage all changes with git add.

    Args:
        repository_path: Path to repository

    Returns:
        Tuple of (success, error_message)
    """
    add_process = await asyncio.create_subprocess_exec(
        'git', 'add', '.',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repository_path
    )
    stdout, stderr = await add_process.communicate()

    if add_process.returncode != 0:
        error_msg = stderr.decode()
        logger.error(GIT_ADD_FAILURE_LOG.format(error=error_msg))
        return False, GIT_ADD_FAILURE_ERROR.format(error=error_msg, stop=STOP_ON_ERROR)

    return True, ""


def _is_nothing_to_commit(output: str) -> bool:
    """Check if git output indicates nothing to commit.

    Args:
        output: Combined stdout and stderr output

    Returns:
        True if nothing to commit, False otherwise
    """
    output_lower = output.lower()
    return GIT_NOTHING_TO_COMMIT_PATTERN1 in output_lower or GIT_NOTHING_TO_COMMIT_PATTERN2 in output_lower


async def _commit_changes(repository_path: str, commit_message: str) -> Tuple[bool, str]:
    """Commit staged changes.

    Args:
        repository_path: Path to repository
        commit_message: Commit message

    Returns:
        Tuple of (success, error_message)
    """
    commit_process = await asyncio.create_subprocess_exec(
        'git', 'commit', '-m', commit_message,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repository_path
    )
    stdout, stderr = await commit_process.communicate()

    if commit_process.returncode != 0:
        stdout_str = stdout.decode()
        stderr_str = stderr.decode()
        combined_output = stdout_str + stderr_str

        # Check if nothing to commit (this is not an error)
        if _is_nothing_to_commit(combined_output):
            logger.info("No changes to commit - working tree is clean")
            return True, GIT_NOTHING_TO_COMMIT

        # Actual commit error
        logger.error(GIT_COMMIT_FAILURE_LOG.format(stdout=stdout_str, stderr=stderr_str))
        error_msg = stderr_str or stdout_str
        return False, GIT_COMMIT_FAILURE_ERROR.format(error=error_msg, stop=STOP_ON_ERROR)

    return True, ""


async def _configure_git_and_commit(
    repository_path: str, commit_message: str
) -> Tuple[bool, str]:
    """Configure git and commit changes.

    Args:
        repository_path: Path to repository
        commit_message: Commit message

    Returns:
        Tuple of (success, error_message)

    Example:
        >>> success, msg = await _configure_git_and_commit("/repo", "feat: add new feature")
        >>> print(f"Success: {success}, Message: {msg}")
    """
    # Step 1: Create git configuration
    config = GitConfiguration(
        repository_path=repository_path,
        commit_message=commit_message
    )

    # Step 2: Configure git user
    success, error_msg = await _configure_git_user(repository_path, config)
    if not success:
        return success, error_msg

    # Step 3: Stage all changes
    success, error_msg = await _stage_all_changes(repository_path)
    if not success:
        return success, error_msg

    # Step 4: Commit changes
    success, error_msg = await _commit_changes(repository_path, commit_message)
    return success, error_msg


async def _push_to_branch(repository_path: str, branch_name: str) -> tuple[bool, str]:
    """Push changes to remote branch.

    Args:
        repository_path: Path to repository
        branch_name: Branch name

    Returns:
        Tuple of (success, error_message)
    """
    process = await asyncio.create_subprocess_exec(
        "git",
        "push",
        "origin",
        branch_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repository_path,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode()
        logger.error(f"Git push failed: {error_msg}")
        return False, f"ERROR: Failed to push: {error_msg}{STOP_ON_ERROR}"

    return True, ""
