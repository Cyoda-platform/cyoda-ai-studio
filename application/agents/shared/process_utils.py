"""Utility functions for process management."""

import os


async def _is_process_running(pid: int) -> bool:
    """
    Check if a process is still running by PID.

    Args:
        pid: Process ID to check

    Returns:
        True if process is running, False otherwise
    """
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

