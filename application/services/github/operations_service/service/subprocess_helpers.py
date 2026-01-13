"""Subprocess execution helpers for GitHub operations."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Constants
CLONE_TIMEOUT_SECONDS = 300
CHECKOUT_TIMEOUT_SECONDS = 60


async def run_subprocess(
    cmd: List[str],
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    check: bool = False,
) -> Dict[str, Any]:
    """Run subprocess safely.

    Args:
        cmd: Command and arguments list
        cwd: Working directory (optional)
        timeout: Timeout in seconds (optional)
        check: Whether to raise exception on non-zero return code

    Returns:
        Dictionary with returncode, stdout, stderr

    Raises:
        Exception: If check=True and command fails
        asyncio.TimeoutError: If command times out
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            raise asyncio.TimeoutError(f"Command {' '.join(cmd)} timed out")

        if check and process.returncode != 0:
            raise Exception(f"Command {' '.join(cmd)} failed: {stderr.decode()}")

        return {
            "returncode": process.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
        }
    except Exception as e:
        logger.error(f"Subprocess error: {e}")
        raise


async def run_git_cmd(args: List[str], check: bool = True) -> Dict[str, Any]:
    """Helper to run git commands (assumes cwd is already set).

    Args:
        args: Git command arguments (without 'git' prefix)
        check: Whether to raise exception on failure

    Returns:
        Dictionary with returncode, stdout, stderr
    """
    return await run_subprocess(["git"] + args, check=check)
