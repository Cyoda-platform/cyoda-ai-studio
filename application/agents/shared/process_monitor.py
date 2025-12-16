"""
Process monitoring utilities for CLI process management.
Provides status checks and control functions for the process manager.
"""

import logging
from typing import Dict, Any

from application.agents.shared.process_manager import get_process_manager

logger = logging.getLogger(__name__)


async def get_process_status() -> Dict[str, Any]:
    """
    Get current status of CLI process management.

    Returns:
        Dictionary with process status information
    """
    process_manager = get_process_manager()
    active_count = await process_manager.get_active_count()
    active_pids = await process_manager.get_active_pids()

    return {
        "active_processes": active_count,
        "max_allowed": process_manager.max_concurrent_processes,
        "active_pids": sorted(list(active_pids)),
        "can_start_new": active_count < process_manager.max_concurrent_processes,
        "utilization_percent": int((active_count / process_manager.max_concurrent_processes) * 100),
    }


async def kill_all_cli_processes() -> Dict[str, Any]:
    """
    Forcefully terminate all active CLI processes.
    Use with caution - this will interrupt all running builds.

    Returns:
        Dictionary with operation result
    """
    process_manager = get_process_manager()
    active_pids = await process_manager.get_active_pids()
    
    logger.warning(f"Killing all {len(active_pids)} active CLI processes: {active_pids}")
    await process_manager.kill_all_processes()

    return {
        "status": "success",
        "killed_count": len(active_pids),
        "killed_pids": sorted(list(active_pids)),
    }


async def get_process_limit() -> int:
    """Get the current process limit."""
    process_manager = get_process_manager()
    return process_manager.max_concurrent_processes


async def set_process_limit(max_concurrent: int) -> Dict[str, Any]:
    """
    Set a new process limit.

    Args:
        max_concurrent: New maximum concurrent processes

    Returns:
        Dictionary with operation result
    """
    if max_concurrent < 1:
        return {
            "status": "error",
            "message": "Process limit must be at least 1",
        }

    process_manager = get_process_manager()
    old_limit = process_manager.max_concurrent_processes
    process_manager.max_concurrent_processes = max_concurrent

    logger.info(f"Process limit changed from {old_limit} to {max_concurrent}")

    return {
        "status": "success",
        "old_limit": old_limit,
        "new_limit": max_concurrent,
    }

