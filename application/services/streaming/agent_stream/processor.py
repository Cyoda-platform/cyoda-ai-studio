"""Agent stream processor - core streaming logic."""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from google.genai import types

from application.services.streaming.constants import (
    HEARTBEAT_INTERVAL,
    MAX_EVENTS_PER_STREAM,
    STREAM_TIMEOUT,
)
from application.services.streaming.event_handlers import EventHandlers
from application.services.streaming.events import StreamEvent
from application.services.streaming.loop_detector import LoopDetector
from application.services.streaming.session_manager import (
    load_or_create_session,
)

logger = logging.getLogger(__name__)


class AgentStreamProcessor:
    """Processes agent execution stream and yields SSE events."""

    def __init__(
        self,
        agent_wrapper: Any,
        user_message: str,
        conversation_history: list[dict[str, str]],
        conversation_id: str,
        adk_session_id: Optional[str],
        user_id: str,
    ):
        self.agent_wrapper = agent_wrapper
        self.user_message = user_message
        self.conversation_history = conversation_history
        self.conversation_id = conversation_id
        self.adk_session_id = adk_session_id
        self.user_id = user_id

        self.event_counter = 0
        self.response_text = ""
        self.session = None
        self.session_technical_id = None
        self.error_occurred = False
        self.error_details = None
        self.events_processed = False
        self.max_response_reached = False

        self.tool_hooks_from_stream = []
        self.ui_functions_from_stream = []
        self.loop_detector = LoopDetector()
        self.event_handlers = EventHandlers(self)

    async def process(self) -> AsyncGenerator[str, None]:
        """Process agent stream and yield SSE events."""
        try:
            yield self._send_start_event()
            await self._initialize_session()
            async for event in self._process_agent_stream():
                if "event: done" in event:
                    logger.info(
                        f"🔄 [process] Yielding DONE event from _process_agent_stream"
                    )
                yield event
        except Exception as e:
            yield self._handle_error(e)
        finally:
            logger.info(
                f"🔚 [process] Entering finally block, calling _finalize_stream()"
            )
            from .finalization import finalize_stream

            async for event in finalize_stream(self):
                if "event: done" in event:
                    logger.info(
                        f"🔚 [process] Yielding DONE event from _finalize_stream()"
                    )
                yield event
            logger.info(
                f"🔚 [process] Finished yielding events from _finalize_stream()"
            )

    def _send_start_event(self) -> str:
        """Send initial start event."""
        event = StreamEvent(
            event_type="start",
            data={
                "message": "Agent started processing",
                "conversation_id": self.conversation_id,
            },
            event_id=str(self.event_counter),
        )
        self.event_counter += 1
        return event.to_sse()

    async def _initialize_session(self) -> None:
        """Initialize or load session."""
        session_state = {}

        if self.conversation_id and hasattr(self.agent_wrapper, "_load_session_state"):
            session_state = await self.agent_wrapper._load_session_state(
                self.conversation_id
            )

        session_state.update(
            {
                "conversation_history": self.conversation_history,
                "user_id": self.user_id,
                "conversation_id": self.conversation_id,
            }
        )

        logger.info(
            f"Streaming for session_id={self.conversation_id}, user_id={self.user_id}, "
            f"adk_session_id={self.adk_session_id}"
        )

        self.session, self.session_technical_id = await load_or_create_session(
            self.agent_wrapper,
            self.conversation_id,
            self.adk_session_id,
            self.user_id,
            session_state,
        )

    async def _process_agent_stream(self) -> AsyncGenerator[str, None]:
        """Process events from agent runner."""
        from .event_processing import process_agent_stream_events

        async for event in process_agent_stream_events(self):
            yield event

    def _handle_error(self, error: Exception) -> str:
        """Handle error during processing."""
        self.error_occurred = True
        self.error_details = {
            "error": str(error),
            "error_type": type(error).__name__,
            "message": "An error occurred during processing",
        }

        if hasattr(error, "response") and hasattr(error.response, "status_code"):
            self.error_details["status_code"] = error.response.status_code
        if hasattr(error, "code"):
            self.error_details["error_code"] = error.code

        logger.error(f"Error during streaming: {error}", exc_info=True)

        event = StreamEvent(
            event_type="error",
            data=self.error_details,
            event_id=str(self.event_counter),
        )
        self.event_counter += 1
        return event.to_sse()


__all__ = ["AgentStreamProcessor"]
