"""Stream finalization and cleanup."""

import logging
from typing import Any, AsyncGenerator

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from application.services.streaming.events import StreamEvent
from application.services.streaming.session_manager import save_session_state

logger = logging.getLogger(__name__)


async def finalize_stream(processor: Any) -> AsyncGenerator[str, None]:
    """Finalize stream and send done event.

    IMPORTANT: Session flush happens BEFORE done event to ensure:
    1. All events are persisted to database
    2. Session is immediately searchable for next message
    3. Chat history is available for conversation continuity

    Args:
        processor: AgentStreamProcessor instance

    Yields:
        Final SSE events
    """
    logger.info(f"🔚 [_finalize_stream] Starting finalization for session {processor.conversation_id}")
    try:
        # Step 1: Save final session state
        await _save_final_session_state(processor)

        # Step 2: Cleanup hooks and temporary state
        await _cleanup_session_state(processor)

        # Step 3: CRITICAL - Flush session to database BEFORE done event
        # This ensures the session with all events is persisted and searchable
        # before the client receives confirmation
        await _flush_session(processor)

        # Step 4: Send done event only after session is fully persisted
        done_event = _send_done_event(processor)
        logger.info(f"🔚 [_finalize_stream] Session flushed, yielding done event")
        yield done_event
    except Exception as e:
        logger.warning(f"Error during finalization: {e}")

    logger.info(
        f"Stream closed for session {processor.conversation_id}, "
        f"error_occurred={processor.error_occurred}, "
        f"events_processed={processor.events_processed}"
    )


async def _save_final_session_state(processor: Any) -> None:
    """Save final session state.

    Args:
        processor: AgentStreamProcessor instance
    """
    try:
        final_session_state = dict(processor.session.state) if processor.session else {}

        if processor.session_technical_id and hasattr(
            processor.agent_wrapper.runner.session_service, "get_pending_state_delta"
        ):
            pending_delta = (
                processor.agent_wrapper.runner.session_service.get_pending_state_delta(
                    processor.session_technical_id
                )
            )
            if pending_delta:
                logger.info(f"📦 Merging {len(pending_delta)} pending state changes")
                final_session_state.update(pending_delta)

        await save_session_state(
            processor.agent_wrapper,
            processor.conversation_id,
            final_session_state,
        )
    except Exception as e:
        logger.warning(f"Error saving session state: {e}")


def _send_done_event(processor: Any) -> str:
    """Send done event with final data.

    Args:
        processor: AgentStreamProcessor instance

    Returns:
        Done event SSE string
    """
    done_message = (
        "Stream ended due to error"
        if processor.error_occurred
        else "Agent completed processing"
    )

    final_hook = None
    if processor.tool_hooks_from_stream:
        final_hook = processor.tool_hooks_from_stream[-1]
        logger.info(
            f"🎣 Using hook from stream "
            f"(collected {len(processor.tool_hooks_from_stream)} hooks)"
        )

    done_data = {
        "message": done_message,
        "response": processor.response_text,
        "adk_session_id": processor.session_technical_id,
        "ui_functions": processor.ui_functions_from_stream,
        "hook": final_hook,
        "hooks": processor.tool_hooks_from_stream if processor.tool_hooks_from_stream else None,
        "total_events": processor.event_counter,
    }

    if processor.error_occurred and processor.error_details:
        done_data.update(processor.error_details)
        done_data["error_context"] = {
            "events_processed": processor.events_processed,
            "response_length": len(processor.response_text),
            "event_count": processor.event_counter,
            "session_id": processor.session_technical_id,
        }

    event = StreamEvent(
        event_type="done",
        data=done_data,
        event_id=str(processor.event_counter),
    )
    return event.to_sse()


async def _cleanup_session_state(processor: Any) -> None:
    """Clean up hooks and ui_functions from session state.

    Args:
        processor: AgentStreamProcessor instance
    """
    state_cleanup = {}

    if processor.session and "last_tool_hook" in processor.session.state:
        del processor.session.state["last_tool_hook"]
        state_cleanup["last_tool_hook"] = None
        logger.info("🧹 Cleared last_tool_hook from session state")

    if processor.session and "ui_functions" in processor.session.state:
        del processor.session.state["ui_functions"]
        state_cleanup["ui_functions"] = None
        logger.info("🧹 Cleared ui_functions from session state")

    if not state_cleanup:
        return

    try:
        event = Event(
            invocation_id=f"cleanup-{processor.session_technical_id}",
            author="system",
            actions=EventActions(state_delta=state_cleanup),
        )
        await processor.agent_wrapper.runner.session_service.append_event(
            session=processor.session, event=event
        )
        logger.info(f"✅ Persisted state cleanup: {list(state_cleanup.keys())}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to persist state cleanup: {e}")


async def _flush_session(processor: Any) -> None:
    """Flush pending events to database.

    Args:
        processor: AgentStreamProcessor instance
    """
    if not processor.session_technical_id or not hasattr(
        processor.agent_wrapper.runner.session_service, "flush_session"
    ):
        return

    try:
        pending_count = (
            processor.agent_wrapper.runner.session_service.get_pending_event_count(
                processor.session_technical_id
            )
        )
        if pending_count > 0:
            logger.info(f"🔄 Flushing {pending_count} pending events")
            flush_success = (
                await processor.agent_wrapper.runner.session_service.flush_session(
                    processor.session_technical_id
                )
            )
            if flush_success:
                logger.info(f"✅ Successfully flushed session")
            else:
                logger.warning(f"⚠️ Failed to flush session")
    except Exception as e:
        logger.error(f"❌ Error flushing session: {e}")


__all__ = [
    "finalize_stream",
    "_save_final_session_state",
    "_send_done_event",
    "_cleanup_session_state",
    "_flush_session",
]
