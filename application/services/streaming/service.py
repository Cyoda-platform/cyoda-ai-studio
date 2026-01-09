"""Streaming Service for Real-Time Agent Updates.

Provides Server-Sent Events (SSE) streaming for real-time agent execution updates.
Supports streaming of:
- Agent transitions (which agent is active)
- Tool executions (which tools are being called)
- Content chunks (streaming LLM responses)
- Progress updates (for long-running operations)
- Error states

Based on Google ADK streaming patterns and SSE best practices.
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Optional, Tuple

from google.genai import types

from application.services.streaming.agent_stream import AgentStreamProcessor
from application.services.streaming.constants import (
    HEARTBEAT_INTERVAL,
    STREAM_TIMEOUT,
)
from application.services.streaming.events import StreamEvent

logger = logging.getLogger(__name__)


class StreamingService:
    """Service for streaming agent execution events via SSE."""

    @staticmethod
    async def stream_agent_response(
        agent_wrapper: Any,
        user_message: str,
        conversation_history: list[dict[str, str]],
        conversation_id: str,
        adk_session_id: Optional[str],
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """Stream agent response with real-time updates.

        Yields SSE-formatted events as the agent processes the message.

        Args:
            agent_wrapper: CyodaAssistantWrapper instance
            user_message: User's message
            conversation_history: Previous messages
            conversation_id: Conversation ID
            adk_session_id: ADK session ID (if exists)
            user_id: User ID

        Yields:
            SSE-formatted event strings
        """
        processor = AgentStreamProcessor(
            agent_wrapper=agent_wrapper,
            user_message=user_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            adk_session_id=adk_session_id,
            user_id=user_id,
        )

        async for event in processor.process():
            yield event

    @staticmethod
    async def stream_progress_updates(
        task_id: str,
        task_service: Any,
        poll_interval: int = 3,
    ) -> AsyncGenerator[str, None]:
        """Stream background task progress updates.

        Polls task service and streams progress events. Sends heartbeats to
        prevent client timeouts. Completes when task reaches terminal state.

        Args:
            task_id: Background task ID.
            task_service: Task service instance.
            poll_interval: Seconds between polls (default: 3).

        Yields:
            SSE-formatted progress events.
        """
        from application.services.streaming.progress_stream import (
            ProgressStreamProcessor,
        )

        processor = ProgressStreamProcessor(
            task_id=task_id,
            task_service=task_service,
            poll_interval=poll_interval,
        )

        async for event in processor.process():
            yield event

    @staticmethod
    def _build_progress_event(
        task_id: str, task: Any, event_counter: int
    ) -> Tuple[str, int]:
        """Build progress event from task.

        Args:
            task_id: Task ID
            task: Task object with progress, status, statistics
            event_counter: Current event counter

        Returns:
            Tuple of (SSE event string, updated counter)
        """
        event = StreamEvent(
            event_type="progress",
            data={
                "task_id": task_id,
                "progress": task.progress,
                "status": task.status,
                "statistics": task.statistics or {},
            },
            event_id=str(event_counter),
        )
        return event.to_sse(), event_counter + 1

    @staticmethod
    def _build_heartbeat_event() -> str:
        """Build heartbeat event for SSE keep-alive.

        Returns:
            SSE heartbeat comment string
        """
        return ": heartbeat\n\n"

    @staticmethod
    async def _check_heartbeat_and_yield(
        last_beat: float, interval: int
    ) -> Tuple[Optional[str], float]:
        """Check if heartbeat should be sent.

        Args:
            last_beat: Timestamp of last heartbeat
            interval: Seconds between heartbeats

        Returns:
            Tuple of (heartbeat event or None, current time)
        """
        current_time = asyncio.get_event_loop().time()
        if current_time - last_beat >= interval:
            return StreamingService._build_heartbeat_event(), current_time
        return None, current_time

    @staticmethod
    def _is_task_complete(task: Any) -> bool:
        """Check if task is in terminal state.

        Args:
            task: Task object with status

        Returns:
            True if task is completed, failed, or cancelled
        """
        return task.status in ["completed", "failed", "cancelled"]

    @staticmethod
    def _build_completion_event(task_id: str, task: Any, event_counter: int) -> str:
        """Build completion event from task.

        Args:
            task_id: Task ID
            task: Task object with status, result, error
            event_counter: Current event counter

        Returns:
            SSE event string
        """
        return StreamEvent(
            event_type="done",
            data={
                "task_id": task_id,
                "status": task.status,
                "result": task.result,
                "error": task.error,
            },
            event_id=str(event_counter),
        ).to_sse()
