"""Progress stream processing for background task monitoring."""

import asyncio
import logging
from typing import Any, AsyncGenerator

from application.services.streaming.events import StreamEvent

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 20
POLL_INTERVAL = 3


class ProgressStreamProcessor:
    """Processes background task progress and yields SSE events."""

    def __init__(
        self,
        task_id: str,
        task_service: Any,
        poll_interval: int = POLL_INTERVAL,
    ):
        self.task_id = task_id
        self.task_service = task_service
        self.poll_interval = poll_interval
        self.event_counter = 0
        self.last_progress = -1

    async def process(self) -> AsyncGenerator[str, None]:
        """Process task progress and yield SSE events."""
        try:
            yield self._send_start_event()
            async for event in self._poll_task_progress():
                yield event
        except Exception as e:
            yield self._handle_error(e)

    def _send_start_event(self) -> str:
        """Send initial start event."""
        event = StreamEvent(
            event_type="start",
            data={
                "message": "Monitoring task progress",
                "task_id": self.task_id,
            },
            event_id=str(self.event_counter),
        )
        self.event_counter += 1
        return event.to_sse()

    async def _poll_task_progress(self) -> AsyncGenerator[str, None]:
        """Poll task status and yield progress events."""
        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            task = await self.task_service.get_task(self.task_id)

            if not task:
                yield StreamEvent(
                    event_type="error",
                    data={
                        "error": "Task not found",
                        "task_id": self.task_id,
                    },
                    event_id=str(self.event_counter),
                ).to_sse()
                break

            if task.progress != self.last_progress:
                self.last_progress = task.progress
                yield self._build_progress_event(task)
                last_heartbeat = asyncio.get_event_loop().time()
            else:
                heartbeat_event = self._check_heartbeat(last_heartbeat)
                if heartbeat_event:
                    yield heartbeat_event
                    last_heartbeat = asyncio.get_event_loop().time()

            if self._is_task_complete(task):
                yield self._build_completion_event(task)
                break

            await asyncio.sleep(self.poll_interval)

    def _build_progress_event(self, task: Any) -> str:
        """Build progress event from task."""
        event = StreamEvent(
            event_type="progress",
            data={
                "task_id": self.task_id,
                "progress": task.progress,
                "status": task.status,
                "statistics": task.statistics or {},
            },
            event_id=str(self.event_counter),
        )
        self.event_counter += 1
        return event.to_sse()

    def _check_heartbeat(self, last_heartbeat: float) -> str | None:
        """Check if heartbeat should be sent."""
        current_time = asyncio.get_event_loop().time()
        if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
            return f": heartbeat {int(current_time)}\n\n"
        return None

    def _is_task_complete(self, task: Any) -> bool:
        """Check if task is in terminal state."""
        return task.status in ["completed", "failed", "cancelled"]

    def _build_completion_event(self, task: Any) -> str:
        """Build completion event from task."""
        return StreamEvent(
            event_type="done",
            data={
                "task_id": self.task_id,
                "status": task.status,
                "result": task.result,
                "error": task.error,
            },
            event_id=str(self.event_counter),
        ).to_sse()

    def _handle_error(self, error: Exception) -> str:
        """Handle error during processing."""
        logger.error(f"Error streaming task progress: {error}", exc_info=True)
        event = StreamEvent(
            event_type="error",
            data={
                "error": str(error),
                "task_id": self.task_id,
            },
            event_id=str(self.event_counter),
        )
        self.event_counter += 1
        return event.to_sse()

