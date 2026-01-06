"""Local git operations (staging, committing, pushing, pulling).

This module contains functions for:
- File staging (git add)
- Commits (git commit)
- Pushes to remote (git push)
- Pulls from remote (git pull, fetch, diff)
- Clone operations
- Git configuration
"""

import asyncio
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

# Configuration constants for git operations
DEFAULT_MERGE_STRATEGY = "recursive"
MERGE_STRATEGY_OPTION = "theirs"
GIT_CONFIG_PULL_REBASE = "false"
NO_CHANGES_TO_PULL_MSG = "No changes to pull"
NOTHING_TO_COMMIT_MSG = "nothing to commit"


async def add_files_to_git(clone_dir: str, file_paths: List[str]) -> Optional[str]:
    """Add files to git staging area.

    Args:
        clone_dir: Repository directory.
        file_paths: List of file paths to add.

    Returns:
        Error message if any file failed to add, None if successful.
    """
    for file_path in file_paths:
        logger.info(f"Adding file to git: {file_path}")
        add_process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'add', file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await add_process.communicate()
        if add_process.returncode != 0:
            error_msg = f"Error during git add {file_path}: {stderr.decode()}"
            logger.error(error_msg)
            return error_msg
        else:
            logger.info(f"Successfully added file: {file_path}")
    return None


async def commit_changes(clone_dir: str, commit_message: str, git_branch_id: str) -> Optional[str]:
    """Commit staged changes to git.

    Args:
        clone_dir: Repository directory.
        commit_message: Commit message.
        git_branch_id: Branch ID (appended to message).

    Returns:
        Error message if commit failed or "nothing to commit", None if successful.
    """
    # Check git status before committing
    status_process = await asyncio.create_subprocess_exec(
        'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
        'status', '--short',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    status_stdout, status_stderr = await status_process.communicate()
    logger.info(f"Git status before commit: {status_stdout.decode().strip()}")

    commit_process = await asyncio.create_subprocess_exec(
        'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
        'commit', '-m', f"{commit_message}: {git_branch_id}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await commit_process.communicate()
    stdout_str = stdout.decode().strip()
    stderr_str = stderr.decode().strip()

    logger.info(f"Git commit stdout: {stdout_str}")
    logger.info(f"Git commit stderr: {stderr_str}")
    logger.info(f"Git commit return code: {commit_process.returncode}")

    if commit_process.returncode != 0:
        # Check if the error is "nothing to commit" - not a real error
        if "nothing to commit" in stdout_str.lower() or "nothing to commit" in stderr_str.lower():
            logger.info(NOTHING_TO_COMMIT_MSG)
            return NOTHING_TO_COMMIT_MSG
        error_msg = f"Error during git commit: stdout='{stdout_str}', stderr='{stderr_str}'"
        logger.error(error_msg)
        return error_msg

    return None


async def push_to_remote(clone_dir: str, git_branch_id: str) -> Optional[str]:
    """Push changes to remote repository.

    Args:
        clone_dir: Repository directory.
        git_branch_id: Branch ID to push.

    Returns:
        Error message if push failed, None if successful.
    """
    push_process = await asyncio.create_subprocess_exec(
        'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
        'push', '-u', 'origin', str(git_branch_id),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await push_process.communicate()
    if push_process.returncode != 0:
        error_msg = f"Error during git push: {stderr.decode()}"
        logger.error(error_msg)
        return error_msg

    logger.info("Git push successful!")
    return None


async def run_git_fetch(clone_dir: str) -> tuple[bool, Optional[str]]:
    """Fetch latest changes from remote.

    Args:
        clone_dir: Repository directory

    Returns:
        Tuple of (success, error_message)
    """
    fetch_process = await asyncio.create_subprocess_exec(
        "git", "--git-dir", f"{clone_dir}/.git", "--work-tree", clone_dir,
        "fetch", "origin",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    fetch_stdout, fetch_stderr = await fetch_process.communicate()

    if fetch_process.returncode != 0:
        error_msg = f"Error during git fetch: {fetch_stderr.decode()}"
        logger.error(error_msg)
        return False, error_msg

    return True, None


async def run_git_diff(clone_dir: str, git_branch_id: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Get diff between local and remote branch.

    Args:
        clone_dir: Repository directory
        git_branch_id: Branch ID

    Returns:
        Tuple of (success, error_message, diff_result)
    """
    diff_process = await asyncio.create_subprocess_exec(
        "git", "--git-dir", f"{clone_dir}/.git", "--work-tree", clone_dir,
        "diff", f"origin/{str(git_branch_id)}", str(git_branch_id),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    diff_stdout, diff_stderr = await diff_process.communicate()

    if diff_process.returncode != 0:
        error_msg = f"Error during git diff: {diff_stderr.decode()}"
        logger.error(error_msg)
        return False, error_msg, None

    diff_result = diff_stdout.decode()
    logger.info(f"Git diff (before pull): {diff_result}")
    return True, None, diff_result


async def configure_pull_strategy(clone_dir: str) -> bool:
    """Configure git pull to use merge strategy (not rebase).

    Args:
        clone_dir: Repository directory

    Returns:
        True if configuration succeeded
    """
    config_process = await asyncio.create_subprocess_exec(
        "git", "--git-dir", f"{clone_dir}/.git", "--work-tree", clone_dir,
        "config", "pull.rebase", GIT_CONFIG_PULL_REBASE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    config_stdout, config_stderr = await config_process.communicate()

    if config_process.returncode != 0:
        logger.warning(f"Warning: Failed to set git pull.rebase config: {config_stderr.decode()}")
        return False

    logger.info("Git pull.rebase set to false (merge strategy)")
    return True


async def run_git_pull(
    clone_dir: str, git_branch_id: str, merge_strategy: str
) -> tuple[bool, Optional[str]]:
    """Execute git pull with specified merge strategy.

    Args:
        clone_dir: Repository directory
        git_branch_id: Branch ID
        merge_strategy: Git merge strategy to use

    Returns:
        Tuple of (success, error_message)
    """
    pull_process = await asyncio.create_subprocess_exec(
        "git", "--git-dir", f"{clone_dir}/.git", "--work-tree", clone_dir,
        "pull", "--strategy", merge_strategy, f"--strategy-option={MERGE_STRATEGY_OPTION}",
        "origin", str(git_branch_id),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    pull_stdout, pull_stderr = await pull_process.communicate()

    if pull_process.returncode != 0:
        error_msg = f"Error during git pull: {pull_stderr.decode()}"
        logger.error(error_msg)
        return False, error_msg

    logger.info(f"Git pull successful: {pull_stdout.decode()}")
    return True, None


async def perform_git_clone(repo_url: str, clone_dir: str) -> Optional[str]:
    """Perform git clone operation.

    Args:
        repo_url: Repository URL (possibly authenticated).
        clone_dir: Directory to clone into.

    Returns:
        Error message if clone failed, None if successful.
    """
    clone_process = await asyncio.create_subprocess_exec(
        'git', 'clone', repo_url, clone_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await clone_process.communicate()

    if clone_process.returncode != 0:
        error_msg = f"Error during git clone: {stderr.decode()}"
        logger.error(error_msg)
        return error_msg

    return None


async def run_git_config():
    """Configure git pull behavior."""
    process = await asyncio.create_subprocess_exec(
        "git", "config", "pull.rebase", "false", "--global",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"Command failed with error: {stderr.decode().strip()}")
    logger.info(f"Git config set: {stdout.decode().strip()}")


async def repo_exists(path: str) -> bool:
    """Check if path exists."""
    return await asyncio.to_thread(os.path.exists, path)
