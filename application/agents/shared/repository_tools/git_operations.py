"""Git Operations module."""

import asyncio
import logging
from typing import Optional

from application.services.github.auth.installation_token_manager import InstallationTokenManager
from application.services.github.repository.url_parser import parse_repository_url
from common.exception.exceptions import InvalidTokenException

logger = logging.getLogger(__name__)


async def _run_git_command(
    cmd: list[str],
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Run a git command asynchronously.

    Args:
        cmd: Command as list of strings
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
        return process.returncode, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", str(e)




async def _get_git_diff(repository_path: str) -> str:
    """
    Get git diff stats for the repository.

    Args:
        repository_path: Path to repository

    Returns:
        Git diff output or empty string
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--stat",
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return stdout.decode("utf-8", errors="replace") if stdout else ""
        else:
            return ""
    except Exception as e:
        logger.warning(f"Failed to get git diff: {e}")
        return ""


# Progress notifications are now handled entirely by BackgroundTask entity
# No need to send messages to conversation anymore




async def _get_authenticated_repo_url_sync(repository_url: str, installation_id: str) -> str:
    """
    Get authenticated repository URL for git operations (fully async).

    Args:
        repository_url: Repository URL (e.g., "https://github.com/owner/repo")
        installation_id: GitHub App installation ID

    Returns:
        Authenticated URL (e.g., "https://x-access-token:TOKEN@github.com/owner/repo.git")
    """
    try:
        # Get token asynchronously (no blocking!)
        token_manager = InstallationTokenManager()
        token = await token_manager.get_installation_token(int(installation_id))

        # Parse URL and create authenticated version
        url_info = parse_repository_url(repository_url)
        authenticated_url = url_info.to_authenticated_url(token)

        logger.info(f"✅ Generated authenticated URL for {url_info.owner}/{url_info.repo_name}")
        return authenticated_url

    except Exception as e:
        logger.error(f"❌ Failed to generate authenticated URL: {e}")
        # Return original URL as fallback (will likely fail for private repos)
        return repository_url



