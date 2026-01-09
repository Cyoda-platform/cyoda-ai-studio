"""Utilities for process management and monitoring."""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def _is_process_running(pid: int) -> bool:
    """
    Check if a process with the given PID is still running.

    Uses os.kill with signal 0 to check if the process exists without sending a signal.
    This is a non-blocking check that works on Unix-like systems.

    Args:
        pid: Process ID to check

    Returns:
        True if the process is running, False otherwise
    """
    try:
        # Signal 0 checks if process exists without sending a signal
        os.kill(pid, 0)
        return True
    except OSError:
        # Process does not exist or we don't have permission
        return False
