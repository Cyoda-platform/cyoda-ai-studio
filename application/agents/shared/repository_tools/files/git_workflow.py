"""Git operations for file management - commit, push, and authentication."""

import asyncio
import logging
from pathlib import Path

from application.agents.shared.repository_tools.constants import (
    GITHUB_PUBLIC_REPO_INSTALLATION_ID,
    JAVA_PUBLIC_REPO_URL,
    PYTHON_PUBLIC_REPO_URL,
    UNKNOWN_ERROR_MESSAGE,
)
from application.agents.shared.repository_tools.git_operations import (
    _get_authenticated_repo_url_sync,
)

logger = logging.getLogger(__name__)

# Constants for git configuration
GIT_USER_NAME = "Cyoda Agent"
GIT_USER_EMAIL = "agent@cyoda.ai"


async def _configure_git_user(repo_path: Path) -> bool:
    """Configure git user name and email for the repository.

    Args:
        repo_path: Root path of the repository.

    Returns:
        True if configuration succeeded, False otherwise.
    """
    logger.info("🔧 Configuring git user for repository...")

    # Set git user.name
    name_process = await asyncio.create_subprocess_exec(
        "git", "config", "user.name", GIT_USER_NAME,
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    name_stdout, name_stderr = await name_process.communicate()
    if name_process.returncode != 0:
        error_msg = name_stderr.decode('utf-8') if name_stderr else 'Unknown error'
        logger.warning(f"⚠️ Failed to set git user.name: {error_msg}")

    # Set git user.email
    email_process = await asyncio.create_subprocess_exec(
        "git", "config", "user.email", GIT_USER_EMAIL,
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    email_stdout, email_stderr = await email_process.communicate()
    if email_process.returncode != 0:
        error_msg = email_stderr.decode('utf-8') if email_stderr else 'Unknown error'
        logger.warning(f"⚠️ Failed to set git user.email: {error_msg}")

    logger.info("✅ Git user configured")
    return True


async def _add_files_to_git(repo_path: Path, func_req_dir: Path) -> str:
    """Add files to git staging area.

    Args:
        repo_path: Root path of the repository.
        func_req_dir: Directory containing files to add.

    Returns:
        Status message (empty if successful, error message otherwise).
    """
    logger.info(f"📝 Adding files from {func_req_dir} to git...")
    process = await asyncio.create_subprocess_exec(
        "git", "add", str(func_req_dir),
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        stdout_msg = stdout.decode("utf-8") if stdout else ""
        stderr_msg = stderr.decode("utf-8") if stderr else ""
        error_msg = stderr_msg or stdout_msg or UNKNOWN_ERROR_MESSAGE
        logger.error(f"❌ Git add failed: {error_msg}")
        logger.error(f"   stdout: {stdout_msg}")
        logger.error(f"   stderr: {stderr_msg}")
        logger.error(f"   func_req_dir: {func_req_dir}")
        logger.error(f"   repo_path: {repo_path}")
        return error_msg

    logger.info("✅ Files added to git staging area")
    return ""


async def _check_git_status(repo_path: Path) -> str:
    """Check git status before committing.

    Args:
        repo_path: Root path of the repository.

    Returns:
        Git status output.
    """
    process = await asyncio.create_subprocess_exec(
        "git", "status", "--short",
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    status_output = stdout.decode("utf-8") if stdout else ""
    logger.info(f"📊 Git status before commit:\n{status_output}")
    return status_output


async def _commit_files_to_git(repo_path: Path, saved_files: list[str]) -> str:
    """Commit saved files to git.

    Args:
        repo_path: Root path of the repository.
        saved_files: List of saved filenames for the commit message.

    Returns:
        Empty string if successful, error message otherwise.
    """
    commit_message = f"Add functional requirements files: {', '.join(saved_files)}"
    process = await asyncio.create_subprocess_exec(
        "git", "commit", "-m", commit_message,
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        stdout_msg = stdout.decode("utf-8") if stdout else ""
        stderr_msg = stderr.decode("utf-8") if stderr else ""
        error_msg = stderr_msg or stdout_msg or UNKNOWN_ERROR_MESSAGE

        if "nothing to commit" in error_msg.lower():
            logger.info("ℹ️ Files already committed (no changes)")
            return ""

        logger.error(f"❌ Git commit failed: {error_msg}")
        logger.error(f"   stdout: {stdout_msg}")
        logger.error(f"   stderr: {stderr_msg}")
        logger.error(f"   repo_path: {repo_path}")
        return error_msg

    return ""


async def _update_remote_authentication(
    repo_path: Path,
    repository_type: str,
    language: str,
    user_repository_url: str,
    installation_id: str,
) -> None:
    """Update remote URL with fresh authentication token.

    Args:
        repo_path: Root path of the repository.
        repository_type: Type of repository (public or private).
        language: Programming language.
        user_repository_url: User's private repository URL (if applicable).
        installation_id: GitHub installation ID.
    """
    if repository_type not in ["public", "private"]:
        return

    # Determine the repository URL and installation ID to use
    if repository_type == "private" and user_repository_url and installation_id:
        repo_url_to_use = user_repository_url
        installation_id_to_use = installation_id
        logger.info(f"🔐 Refreshing authentication for private repository: {repo_url_to_use}")
    elif repository_type == "public":
        if language.lower() == "python":
            repo_url_to_use = PYTHON_PUBLIC_REPO_URL
        elif language.lower() == "java":
            repo_url_to_use = JAVA_PUBLIC_REPO_URL
        else:
            repo_url_to_use = None
        installation_id_to_use = GITHUB_PUBLIC_REPO_INSTALLATION_ID
        logger.info(f"🔐 Refreshing authentication for public repository: {repo_url_to_use}")
    else:
        return

    if not repo_url_to_use or not installation_id_to_use:
        return

    try:
        authenticated_url = await _get_authenticated_repo_url_sync(repo_url_to_use, installation_id_to_use)

        set_url_process = await asyncio.create_subprocess_exec(
            "git", "remote", "set-url", "origin", authenticated_url,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await set_url_process.communicate()

        if set_url_process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else UNKNOWN_ERROR_MESSAGE
            logger.warning(f"⚠️ Failed to update remote URL: {error_msg}")
        else:
            logger.info("✅ Successfully refreshed remote authentication")
    except Exception as e:
        logger.warning(f"⚠️ Failed to refresh authentication: {e}")


async def _push_to_remote(repo_path: Path, branch_name: str) -> str:
    """Push committed files to remote repository.

    Args:
        repo_path: Root path of the repository.
        branch_name: Git branch name to push to.

    Returns:
        Empty string if successful, error message otherwise.
    """
    process = await asyncio.create_subprocess_exec(
        "git", "push", "--set-upstream", "origin", branch_name,
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode("utf-8") if stderr else UNKNOWN_ERROR_MESSAGE
        logger.warning(f"⚠️ Git push failed (may not have remote): {error_msg}")
        return error_msg

    return ""


async def _commit_and_push_files(
    repo_path: Path,
    branch_name: str,
    func_req_dir: Path,
    saved_files: list[str],
    repository_type: str,
    language: str,
    user_repository_url: str,
    installation_id: str,
) -> str:
    """Commit saved files and push to remote repository.

    Args:
        repo_path: Root path of the repository.
        branch_name: Git branch to push to.
        func_req_dir: Directory containing saved files.
        saved_files: List of saved filenames.
        repository_type: Type of repository (public or private).
        language: Programming language of the repository.
        user_repository_url: User's private repository URL (if applicable).
        installation_id: GitHub installation ID.

    Returns:
        Status message indicating success or error.
    """
    from .file_operations import _log_directory_debug_info

    logger.info(f"📦 Committing and pushing {len(saved_files)} files to branch {branch_name}...")

    try:
        # Configure git user
        await _configure_git_user(repo_path)

        # Stage files
        error_msg = await _add_files_to_git(repo_path, func_req_dir)
        if error_msg:
            return f"ERROR: Failed to add files to git: {error_msg}"

        # Check status before commit
        status_output = await _check_git_status(repo_path)
        if not status_output.strip():
            logger.warning("⚠️ No staged changes detected. Files may not have been added properly.")
            _log_directory_debug_info(func_req_dir, saved_files)

        # Commit files
        error_msg = await _commit_files_to_git(repo_path, saved_files)
        if error_msg:
            return f"ERROR: Failed to commit files: {error_msg}"

        # Refresh authentication and push
        await _update_remote_authentication(
            repo_path, repository_type, language, user_repository_url, installation_id
        )

        error_msg = await _push_to_remote(repo_path, branch_name)
        if error_msg:
            logger.warning(f"⚠️ Git push failed (may not have remote): {error_msg}")
            rel_path = func_req_dir.relative_to(repo_path)
            return (
                f"SUCCESS: Saved {len(saved_files)} file(s) to {rel_path} and committed locally. "
                f"Push to remote failed (may not have remote configured)."
            )

        logger.info(f"🎉 Successfully saved, committed, and pushed {len(saved_files)} files")
        rel_path = func_req_dir.relative_to(repo_path)
        files_str = ', '.join(saved_files)
        return (
            f"SUCCESS: Saved {len(saved_files)} file(s) to {rel_path}, committed, "
            f"and pushed to branch {branch_name}. Files: {files_str}"
        )

    except Exception as e:
        logger.error(f"❌ Failed to commit/push files: {e}", exc_info=True)
        return f"ERROR: Files were saved but failed to commit/push: {str(e)}"
