"""Event processing for agent stream."""

import asyncio
import logging
from typing import Any, AsyncGenerator

from google.genai import types

from application.services.streaming.constants import (
    HEARTBEAT_INTERVAL,
    MAX_EVENTS_PER_STREAM,
    STREAM_TIMEOUT,
)
from application.services.streaming.events import StreamEvent

logger = logging.getLogger(__name__)


async def process_agent_stream_events(processor: Any) -> AsyncGenerator[str, None]:
    """Process events from agent runner.

    Args:
        processor: AgentStreamProcessor instance

    Yields:
        SSE event strings
    """
    adk_runner_session_id = processor.session_technical_id or processor.conversation_id
    stream_start_time = asyncio.get_event_loop().time()
    last_heartbeat = stream_start_time

    logger.info(
        f"🚀 Starting ADK Runner with session_id={adk_runner_session_id} "
        f"(technical_id={processor.session_technical_id})"
    )

    event_stream = processor.agent_wrapper.runner.run_async(
        user_id=processor.user_id,
        session_id=adk_runner_session_id,
        new_message=types.Content(parts=[types.Part(text=processor.user_message)]),
    )

    event_iterator = event_stream.__aiter__()
    stream_active = True

    while stream_active:
        try:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - stream_start_time

            if elapsed > STREAM_TIMEOUT:
                yield _handle_stream_timeout(processor, elapsed)
                break

            event = await asyncio.wait_for(
                event_iterator.__anext__(), timeout=HEARTBEAT_INTERVAL
            )
            processor.events_processed = True
            last_heartbeat = current_time

            async for sse_event in processor.event_handlers.handle_event(event):
                if "event: done" in sse_event:
                    logger.warning(
                        f"⚠️ [_process_agent_stream] WARNING: Received done event from agent runner!"
                    )
                yield sse_event

                if processor.event_counter >= MAX_EVENTS_PER_STREAM:
                    logger.warning(f"Event limit reached ({MAX_EVENTS_PER_STREAM})")
                    stream_active = False
                    break

        except asyncio.TimeoutError:
            yield _send_heartbeat()
            continue
        except StopAsyncIteration:
            logger.info(
                f"✅ Event stream completed (events_processed={processor.events_processed})"
            )
            break

        await asyncio.sleep(0)


def _handle_stream_timeout(processor: Any, elapsed: float) -> str:
    """Handle stream timeout.

    Args:
        processor: AgentStreamProcessor instance
        elapsed: Elapsed time in seconds

    Returns:
        SSE event string
    """
    logger.error(f"⏱️ STREAM TIMEOUT: Exceeded {STREAM_TIMEOUT}s limit.")
    event = StreamEvent(
        event_type="error",
        data={
            "error": "Stream timeout",
            "message": f"⏱️ Stream execution exceeded {STREAM_TIMEOUT} seconds.",
            "elapsed_seconds": int(elapsed),
        },
        event_id=str(processor.event_counter),
    )
    processor.event_counter += 1
    return event.to_sse()


def _send_heartbeat() -> str:
    """Send heartbeat to prevent timeout.

    Returns:
        Heartbeat SSE string
    """
    current_time = asyncio.get_event_loop().time()
    logger.debug(f"💓 Sending heartbeat")
    return f": heartbeat {int(current_time)}\n\n"


__all__ = [
    "process_agent_stream_events",
    "_handle_stream_timeout",
    "_send_heartbeat",
]
