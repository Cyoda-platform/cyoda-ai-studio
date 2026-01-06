"""Event handlers for different event types."""

import logging
from typing import Any, AsyncGenerator, Optional

from application.services.streaming.constants import MAX_RESPONSE_SIZE
from application.services.streaming.events import StreamEvent
from application.services.streaming.event_processor import (
    extract_tool_hook_from_response,
    extract_ui_functions_from_session,
)
from application.services.streaming.hook_normalizer import normalize_hook

logger = logging.getLogger(__name__)


class EventHandlers:
    """Handles different types of ADK events."""

    def __init__(self, processor: Any):
        self.processor = processor
        self.current_agent = None
        self.current_tool = None
        self.current_tool_args = None

    async def handle_event(self, event: Any) -> AsyncGenerator[str, None]:
        """Handle a single ADK event."""
        if self._is_agent_transition(event):
            yield self._handle_agent_transition(event)

        if hasattr(event, "content") and event.content:
            async for sse_event in self._handle_content(event):
                yield sse_event

        if hasattr(event, "actions") and event.actions:
            async for sse_event in self._handle_actions(event):
                yield sse_event

    def _is_agent_transition(self, event: Any) -> bool:
        """Check if event represents agent transition."""
        return (
            hasattr(event, "author")
            and event.author != "user"
            and event.author != self.current_agent
        )

    def _handle_agent_transition(self, event: Any) -> str:
        """Handle agent transition event."""
        self.current_agent = event.author
        sse_event = StreamEvent(
            event_type="agent",
            data={
                "agent_name": self.current_agent,
                "message": f"Agent '{self.current_agent}' is now active",
                "event_id": getattr(event, "id", None),
                "invocation_id": getattr(event, "invocation_id", None),
            },
            event_id=str(self.processor.event_counter),
        )
        self.processor.event_counter += 1
        return sse_event.to_sse()

    async def _handle_content(self, event: Any) -> AsyncGenerator[str, None]:
        """Handle content parts (text, function calls, responses)."""
        if not event.content.parts:
            return

        for part in event.content.parts:
            if hasattr(part, "function_call") and part.function_call:
                async for sse_event in self._handle_function_call(part):
                    yield sse_event
            elif hasattr(part, "function_response") and part.function_response:
                async for sse_event in self._handle_function_response(part):
                    yield sse_event
            elif hasattr(part, "text") and part.text:
                async for sse_event in self._handle_text_content(part):
                    yield sse_event

    async def _handle_function_call(self, part: Any) -> AsyncGenerator[str, None]:
        """Handle function call event."""
        tool_name = part.function_call.name
        tool_args = (
            dict(part.function_call.args)
            if hasattr(part.function_call, "args")
            else {}
        )
        tool_id = getattr(part.function_call, "id", None)

        tool_args_str = str(tool_args)
        loop_error = self.processor.loop_detector.record_tool_call(
            tool_name, tool_args_str
        )

        if loop_error:
            logger.error(loop_error)
            yield StreamEvent(
                event_type="error",
                data={
                    "error": "Infinite loop detected",
                    "message": loop_error,
                    "tool_name": tool_name,
                },
                event_id=str(self.processor.event_counter),
            ).to_sse()
            self.processor.event_counter += 1
            return

        if tool_name != self.current_tool or tool_args != self.current_tool_args:
            self.current_tool = tool_name
            self.current_tool_args = tool_args

            logger.info(
                f"🔧 Tool call detected: {tool_name} (id={tool_id}) "
                f"[call #{self.processor.loop_detector.tool_call_count}]"
            )

            yield StreamEvent(
                event_type="tool_call",
                data={
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_id": tool_id,
                    "message": f"Calling tool: {tool_name}",
                    "agent": self.current_agent,
                },
                event_id=str(self.processor.event_counter),
            ).to_sse()
            self.processor.event_counter += 1

    async def _handle_function_response(self, part: Any) -> AsyncGenerator[str, None]:
        """Handle function response event."""
        tool_name = part.function_response.name
        tool_response = (
            dict(part.function_response.response)
            if hasattr(part.function_response, "response")
            else {}
        )
        tool_id = getattr(part.function_response, "id", None)

        logger.info(f"✅ Tool response received: {tool_name} (id={tool_id})")

        tool_hook = None
        tool_message = None

        if self.processor.session and "last_tool_hook" in self.processor.session.state:
            tool_hook = self.processor.session.state.get("last_tool_hook")

        self.processor.ui_functions_from_stream = (
            extract_ui_functions_from_session(
                self.processor.session,
                self.processor.ui_functions_from_stream,
            )
        )

        tool_message, response_hook = extract_tool_hook_from_response(tool_response)
        if response_hook:
            tool_hook = response_hook
            self.processor.tool_hooks_from_stream.append(tool_hook)
            if self.processor.session:
                self.processor.session.state["last_tool_hook"] = tool_hook

        yield StreamEvent(
            event_type="tool_response",
            data={
                "tool_name": tool_name,
                "tool_id": tool_id,
                "tool_response": tool_message or "",
                "agent": self.current_agent,
                "hook": tool_hook,
            },
            event_id=str(self.processor.event_counter),
        ).to_sse()
        self.processor.event_counter += 1

    async def _handle_text_content(self, part: Any) -> AsyncGenerator[str, None]:
        """Handle text content event."""
        chunk = part.text

        if (
            len(self.processor.response_text) + len(chunk)
            > MAX_RESPONSE_SIZE
        ):
            if not self.processor.max_response_reached:
                self.processor.max_response_reached = True
                logger.warning(f"Response size limit reached ({MAX_RESPONSE_SIZE} bytes)")
                yield StreamEvent(
                    event_type="content",
                    data={
                        "chunk": "\n\n[Response truncated - size limit reached]",
                        "accumulated_length": len(self.processor.response_text),
                        "partial": False,
                        "agent": self.current_agent,
                        "truncated": True,
                    },
                    event_id=str(self.processor.event_counter),
                ).to_sse()
                self.processor.event_counter += 1
            return

        self.processor.response_text += chunk
        is_partial = getattr(part, "partial", False) if hasattr(part, "partial") else False

        yield StreamEvent(
            event_type="content",
            data={
                "chunk": chunk,
                "accumulated_length": len(self.processor.response_text),
                "partial": is_partial,
                "agent": self.current_agent,
            },
            event_id=str(self.processor.event_counter),
        ).to_sse()
        self.processor.event_counter += 1

    async def _handle_actions(self, event: Any) -> AsyncGenerator[str, None]:
        """Handle state and artifact changes."""
        if hasattr(event.actions, "state_delta") and event.actions.state_delta:
            yield StreamEvent(
                event_type="state_change",
                data={
                    "state_delta": dict(event.actions.state_delta),
                    "message": "Session state updated",
                    "agent": self.current_agent,
                },
                event_id=str(self.processor.event_counter),
            ).to_sse()
            self.processor.event_counter += 1

        if hasattr(event.actions, "artifact_delta") and event.actions.artifact_delta:
            yield StreamEvent(
                event_type="artifact_change",
                data={
                    "artifact_delta": {
                        k: str(v)
                        for k, v in dict(event.actions.artifact_delta).items()
                    },
                    "message": "Artifacts updated",
                    "agent": self.current_agent,
                },
                event_id=str(self.processor.event_counter),
            ).to_sse()
            self.processor.event_counter += 1

        if (
            hasattr(event.actions, "transfer_to_agent")
            and event.actions.transfer_to_agent
        ):
            yield StreamEvent(
                event_type="agent_transfer",
                data={
                    "from_agent": self.current_agent,
                    "to_agent": event.actions.transfer_to_agent,
                    "message": f"Transferring to agent: {event.actions.transfer_to_agent}",
                },
                event_id=str(self.processor.event_counter),
            ).to_sse()
            self.processor.event_counter += 1

