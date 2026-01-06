import asyncio
import logging
import os
from typing import Optional, Set

logger = logging.getLogger(__name__)


class CLIProcessManager:
    """
    Manages CLI (augment) process lifecycle with PID tracking and limits.
    Prevents runaway processes by enforcing a maximum concurrent process limit.
    """

    def __init__(self, max_concurrent_processes: int = 5):
        """
        Initialize the process manager.

        Args:
            max_concurrent_processes: Maximum number of concurrent CLI processes allowed
        """
        self.max_concurrent_processes = max_concurrent_processes
        self.active_pids: Set[int] = set()
        self._lock = asyncio.Lock()

    async def can_start_process(self, skip_cleanup: bool = False) -> bool:
        """
        Check if a new process can be started without exceeding the limit.

        Args:
            skip_cleanup: If True, skip cleanup of dead processes (for testing)

        Returns:
            True if process can be started, False if limit reached
        """
        async with self._lock:
            # Clean up dead processes
            if not skip_cleanup:
                await self._cleanup_dead_processes()
            return len(self.active_pids) < self.max_concurrent_processes

    async def register_process(self, pid: int, skip_cleanup: bool = False) -> bool:
        """
        Register a new CLI process PID.

        Args:
            pid: Process ID to register
            skip_cleanup: If True, skip cleanup of dead processes (for testing)

        Returns:
            True if registered successfully, False if limit exceeded
        """
        async with self._lock:
            if not skip_cleanup:
                await self._cleanup_dead_processes()
            if len(self.active_pids) >= self.max_concurrent_processes:
                logger.error(
                    f"Cannot start process {pid}: limit of {self.max_concurrent_processes} "
                    f"concurrent processes reached. Active PIDs: {self.active_pids}"
                )
                return False
            self.active_pids.add(pid)
            active_count = len(self.active_pids)
            logger.info(
                f"Registered CLI process PID {pid}. "
                f"Active: {active_count}/{self.max_concurrent_processes}"
            )
            return True

    async def unregister_process(self, pid: int) -> None:
        """
        Unregister a CLI process PID (process completed).

        Args:
            pid: Process ID to unregister
        """
        async with self._lock:
            if pid in self.active_pids:
                self.active_pids.discard(pid)
                active_count = len(self.active_pids)
                logger.info(
                    f"Unregistered CLI process PID {pid}. "
                    f"Active: {active_count}/{self.max_concurrent_processes}"
                )

    async def get_active_count(self) -> int:
        """Get current count of active processes."""
        async with self._lock:
            await self._cleanup_dead_processes()
            return len(self.active_pids)

    async def get_active_pids(self) -> Set[int]:
        """Get set of all active process PIDs."""
        async with self._lock:
            await self._cleanup_dead_processes()
            return self.active_pids.copy()

    async def _cleanup_dead_processes(self) -> None:
        """Remove PIDs of processes that are no longer running."""
        dead_pids = []
        for pid in self.active_pids:
            if not self._is_process_alive(pid):
                dead_pids.append(pid)

        for pid in dead_pids:
            self.active_pids.discard(pid)
            logger.info(f"Cleaned up dead process PID {pid}")

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check if a process is still running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    async def kill_all_processes(self) -> None:
        """Forcefully terminate all active CLI processes."""
        async with self._lock:
            pids_to_kill = self.active_pids.copy()
            for pid in pids_to_kill:
                try:
                    os.kill(pid, 9)  # SIGKILL
                    logger.warning(f"Killed CLI process PID {pid}")
                except (OSError, ProcessLookupError):
                    pass
                self.active_pids.discard(pid)


# Global singleton instance
_process_manager: Optional[CLIProcessManager] = None


def get_process_manager(max_concurrent: int = 5) -> CLIProcessManager:
    """Get or create the global process manager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = CLIProcessManager(max_concurrent_processes=max_concurrent)
    return _process_manager

