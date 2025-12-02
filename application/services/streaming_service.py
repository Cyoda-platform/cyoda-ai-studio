"""
Streaming Service for Real-Time Agent Updates

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
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional
from collections import defaultdict

from google.genai import types
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

logger = logging.getLogger(__name__)


# CLI invocation tracking (in-memory)
class CLIInvocationTracker:
    """Tracks CLI invocations per agent loop to prevent runaway CLI calls."""

    def __init__(self, max_cli_calls: int = 10):
        self.max_cli_calls = max_cli_calls
        # Key: session_id, Value: count of CLI invocations
        self.cli_call_counts = defaultdict(int)

    def record_cli_call(self, session_id: str) -> tuple[bool, str]:
        """
        Record a CLI invocation and check if limit exceeded.

        Returns:
            (is_allowed, message) - is_allowed=False if limit exceeded
        """
        self.cli_call_counts[session_id] += 1
        count = self.cli_call_counts[session_id]

        if count > self.max_cli_calls:
            return False, f"🚫 CLI LIMIT EXCEEDED: {count} CLI invocations in this agent loop (max: {self.max_cli_calls}). Stopping to prevent runaway."

        return True, ""

    def reset_session(self, session_id: str):
        """Reset CLI call count for a session (called at start of new agent loop)."""
        if session_id in self.cli_call_counts:
            del self.cli_call_counts[session_id]

    def get_count(self, session_id: str) -> int:
        """Get current CLI call count for a session."""
        return self.cli_call_counts.get(session_id, 0)


# Global CLI tracker instance
_cli_tracker = CLIInvocationTracker(max_cli_calls=10)


def check_cli_invocation_limit(session_id: str) -> tuple[bool, str]:
    """
    Check if CLI invocation limit has been exceeded for this session.

    Args:
        session_id: The session ID to check

    Returns:
        (is_allowed, message) - is_allowed=False if limit exceeded
    """
    return _cli_tracker.record_cli_call(session_id)


def reset_cli_invocation_count(session_id: str):
    """Reset CLI invocation count for a new agent loop."""
    _cli_tracker.reset_session(session_id)


def get_cli_invocation_count(session_id: str) -> int:
    """Get current CLI invocation count for a session."""
    return _cli_tracker.get_count(session_id)


def normalize_hook(hook: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize hook structure to fix serialization issues.

    Cyoda's JSON serialization sometimes wraps dict values in lists.
    This function fixes the repository_config_selection hook by unwrapping
    the options field if it was incorrectly wrapped in a list.

    Args:
        hook: Hook dictionary to normalize

    Returns:
        Normalized hook dictionary
    """
    if not isinstance(hook, dict):
        return hook

    # Fix repository_config_selection hook options wrapping
    if hook.get("type") == "repository_config_selection":
        if "data" in hook and isinstance(hook["data"], dict):
            options = hook["data"].get("options")
            # If options is a list with one dict element, unwrap it
            if isinstance(options, list) and len(options) == 1 and isinstance(options[0], dict):
                logger.info("🎣 Normalizing hook: unwrapping options from list to dict")
                hook = {
                    **hook,
                    "data": {
                        **hook["data"],
                        "options": options[0]
                    }
                }

    return hook


def format_response_section(title: str, content: str, section_type: str = "info") -> str:
    """
    Format a response section with markdown styling for visual separation.

    Args:
        title: Section title
        content: Section content
        section_type: Type of section (info, tool_response, agent_message, etc.)

    Returns:
        Formatted markdown string with visual separation
    """
    if not content or not content.strip():
        return ""

    # Create markdown formatted section with visual separator
    formatted = f"\n\n---\n\n**{title}:**\n\n{content}"
    return formatted

# Stream timeout in seconds (5 minutes - prevents infinite loops)
STREAM_TIMEOUT = 300

# Memory limits for streaming
MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB limit for accumulated response
MAX_EVENTS_PER_STREAM = 10000    # Limit number of events per stream

# Tool call limits for loop detection
MAX_TOOL_CALLS_PER_STREAM = 50   # Stop if more than 50 tool calls in one stream
MAX_CONSECUTIVE_SAME_TOOL = 7    # Stop if same tool called 3+ times consecutively


class StreamEvent:
    """Represents a streaming event to send to the client."""

    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None,
    ):
        """
        Initialize a stream event.

        Args:
            event_type: Type of event (start, agent, tool, content, progress, error, done)
            data: Event data dictionary
            event_id: Optional event ID for client tracking
        """
        self.event_type = event_type
        self.data = data
        self.event_id = event_id or str(int(datetime.utcnow().timestamp() * 1000))  # Auto-generate ID
        self.timestamp = datetime.utcnow().isoformat()

    def to_sse(self) -> str:
        """
        Convert event to SSE format.

        Returns:
            SSE-formatted string with event type, data, and optional ID
        """
        lines = []

        # Always add event ID for stream resumption
        lines.append(f"id: {self.event_id}")

        # Add event type
        lines.append(f"event: {self.event_type}")

        # Add timestamp to data
        event_data = {**self.data, "timestamp": self.timestamp}

        # Add data (JSON-encoded)
        lines.append(f"data: {json.dumps(event_data)}")

        # SSE format requires double newline at the end
        return "\n".join(lines) + "\n\n"


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
        """
        Stream agent response with real-time updates.

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
        event_counter = 0
        session_id = conversation_id or "default"
        response_text = ""
        session_technical_id = None
        error_occurred = False
        error_details = None  # Store specific error details

        # Memory protection
        max_response_reached = False

        try:
            # Send start event
            yield StreamEvent(
                event_type="start",
                data={
                    "message": "Agent started processing",
                    "conversation_id": conversation_id,
                },
                event_id=str(event_counter),
            ).to_sse()
            event_counter += 1

            # Prepare session state
            session_state = {}

            if conversation_id:
                session_state = await agent_wrapper._load_session_state(conversation_id)

            session_state["conversation_history"] = conversation_history
            session_state["user_id"] = user_id
            session_state["conversation_id"] = conversation_id

            logger.info(
                f"Streaming for session_id={session_id}, user_id={user_id}, "
                f"conversation_id={conversation_id}, adk_session_id={adk_session_id}"
            )

            # Get or create session
            session = None
            if adk_session_id and hasattr(
                agent_wrapper.runner.session_service, "get_session_by_technical_id"
            ):
                adk_session_entity = await agent_wrapper.runner.session_service.get_session_by_technical_id(
                    adk_session_id
                )
                if adk_session_entity:
                    session = agent_wrapper.runner.session_service._to_adk_session(
                        adk_session_entity
                    )
                    session_technical_id = adk_session_id
                    logger.info(
                        f"✅ Loaded existing session via technical_id: {adk_session_id}"
                    )

            if not session:
                session = await agent_wrapper.runner.session_service.get_session(
                    app_name="cyoda-assistant",
                    user_id=user_id,
                    session_id=session_id,
                )
                if session:
                    session_technical_id = session.state.get("__cyoda_technical_id__")
                    logger.info(
                        f"✅ Loaded existing session via search: {session_id}, technical_id={session_technical_id}"
                    )

            if session:
                for key, value in session_state.items():
                    session.state[key] = value
            else:
                # Create new session
                created_session = (
                    await agent_wrapper.runner.session_service.create_session(
                        app_name="cyoda-assistant",
                        user_id=user_id,
                        session_id=session_id,
                        state=session_state,
                    )
                )
                session_technical_id = created_session.state.get(
                    "__cyoda_technical_id__"
                )
                logger.info(
                    f"✅ Created new session: {session_id}, technical_id={session_technical_id}"
                )

            # OPTIMIZATION: Use technical_id as session_id for ADK Runner
            # This way, when ADK Runner calls get_session(session_id=technical_id),
            # our optimized get_session() will recognize it as a UUID and use fast lookup!
            adk_runner_session_id = session_technical_id or session_id

            # Stream agent execution
            current_agent = None
            current_tool = None
            current_tool_args = None

            # Track if we've started processing events
            events_processed = False

            # Heartbeat tracking to prevent proxy/client timeouts
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = 120  # Send heartbeat every 2 minutes (LLM can take 30-60s to respond)

            # Stream timeout tracking
            stream_start_time = asyncio.get_event_loop().time()

            # Tool call tracking for loop detection
            tool_call_history = []
            tool_call_count = 0

            # Track all tool hooks for the done event
            # This persists across loop iterations so we can use it in the finally block
            tool_hooks_from_stream = []

            logger.info(
                f"🚀 Starting ADK Runner with session_id={adk_runner_session_id} (technical_id={session_technical_id})"
            )

            try:
                logger.info(f"🚀 Starting ADK runner.run_async with session_id={adk_runner_session_id}")

                # Create async generator from runner
                event_stream = agent_wrapper.runner.run_async(
                    user_id=user_id,
                    session_id=adk_runner_session_id,  # Use technical_id for fast lookup!
                    new_message=types.Content(parts=[types.Part(text=user_message)]),
                )

                # Convert to async iterator for heartbeat support
                event_iterator = event_stream.__aiter__()
                stream_active = True

                while stream_active:
                    try:
                        # Check for stream timeout (5 minutes max)
                        current_time = asyncio.get_event_loop().time()
                        elapsed = current_time - stream_start_time
                        if elapsed > STREAM_TIMEOUT:
                            logger.error(f"⏱️ STREAM TIMEOUT: Exceeded {STREAM_TIMEOUT}s limit. Stopping stream to prevent runaway.")
                            yield StreamEvent(
                                event_type="error",
                                data={
                                    "error": "Stream timeout",
                                    "message": f"⏱️ Stream execution exceeded {STREAM_TIMEOUT} seconds. Agent stopped to prevent infinite loops.",
                                    "elapsed_seconds": int(elapsed),
                                },
                                event_id=str(event_counter),
                            ).to_sse()
                            event_counter += 1
                            stream_active = False
                            break

                        # Wait for next event with timeout for heartbeat
                        event = await asyncio.wait_for(
                            event_iterator.__anext__(),
                            timeout=heartbeat_interval
                        )
                        events_processed = True
                        last_heartbeat = asyncio.get_event_loop().time()  # Reset heartbeat on event
                    except asyncio.TimeoutError:
                        # No event received within heartbeat interval - send heartbeat
                        current_time = asyncio.get_event_loop().time()
                        logger.debug(f"💓 Sending heartbeat (no events for {heartbeat_interval}s)")
                        yield f": heartbeat {int(current_time)}\n\n"
                        last_heartbeat = current_time
                        continue  # Continue waiting for next event
                    except StopAsyncIteration:
                        # Stream completed normally (upstream closed event stream)
                        # Log whether we actually saw any events; if events_processed is False,
                        # this usually means the model/ADK ended before producing any tokens.
                        logger.info(
                            "✅ Event stream completed (events_processed=%s)",
                            events_processed,
                        )
                        stream_active = False
                        break
                    # Detect agent transitions
                    if (
                        hasattr(event, "author")
                        and event.author != "user"
                        and event.author != current_agent
                    ):
                        current_agent = event.author
                        yield StreamEvent(
                            event_type="agent",
                            data={
                                "agent_name": current_agent,
                                "message": f"Agent '{current_agent}' is now active",
                                "event_id": getattr(event, "id", None),
                                "invocation_id": getattr(event, "invocation_id", None),
                            },
                            event_id=str(event_counter),
                        ).to_sse()
                        event_counter += 1

                    # Detect tool calls (function calls)
                    if hasattr(event, "content") and event.content:
                        if event.content.parts:
                            for part in event.content.parts:
                                # Check for function call
                                if hasattr(part, "function_call") and part.function_call:
                                    tool_name = part.function_call.name
                                    tool_args = (
                                        dict(part.function_call.args)
                                        if hasattr(part.function_call, "args")
                                        else {}
                                    )
                                    tool_id = getattr(part.function_call, "id", None)

                                    # Track ALL tool calls for loop detection (not just unique ones)
                                    tool_call_key = (tool_name, str(tool_args))
                                    tool_call_history.append(tool_call_key)
                                    tool_call_count += 1

                                    # Check if too many tool calls
                                    if tool_call_count > MAX_TOOL_CALLS_PER_STREAM:
                                        logger.error(f"🔄 LOOP DETECTED: Exceeded {MAX_TOOL_CALLS_PER_STREAM} tool calls. Stopping stream.")
                                        yield StreamEvent(
                                            event_type="error",
                                            data={
                                                "error": "Too many tool calls",
                                                "message": f"🔄 Agent made {tool_call_count} tool calls. Stopping to prevent infinite loop.",
                                                "tool_call_count": tool_call_count,
                                            },
                                            event_id=str(event_counter),
                                        ).to_sse()
                                        event_counter += 1
                                        stream_active = False
                                        break

                                    # Check for consecutive identical tool calls (same tool + same args)
                                    if len(tool_call_history) >= MAX_CONSECUTIVE_SAME_TOOL:
                                        recent = tool_call_history[-MAX_CONSECUTIVE_SAME_TOOL:]
                                        if all(call == recent[0] for call in recent):
                                            logger.error(f"🔄 LOOP DETECTED: Tool '{tool_name}' called {MAX_CONSECUTIVE_SAME_TOOL} times with identical args. Stopping stream.")
                                            yield StreamEvent(
                                                event_type="error",
                                                data={
                                                    "error": "Infinite loop detected",
                                                    "message": f"🔄 Tool '{tool_name}' called {MAX_CONSECUTIVE_SAME_TOOL} times in a row with identical arguments. Agent stopped to prevent infinite loop.",
                                                    "tool_name": tool_name,
                                                },
                                                event_id=str(event_counter),
                                            ).to_sse()
                                            event_counter += 1
                                            stream_active = False
                                            break

                                    # Only emit SSE event if tool/args changed (avoid duplicate events)
                                    if (
                                        tool_name != current_tool
                                        or tool_args != current_tool_args
                                    ):
                                        current_tool = tool_name
                                        current_tool_args = tool_args

                                        logger.info(f"🔧 Tool call detected: {tool_name} (id={tool_id}) [call #{tool_call_count}]")

                                        yield StreamEvent(
                                            event_type="tool_call",
                                            data={
                                                "tool_name": tool_name,
                                                "tool_args": tool_args,
                                                "tool_id": tool_id,
                                                "message": f"Calling tool: {tool_name}",
                                                "agent": current_agent,
                                            },
                                            event_id=str(event_counter),
                                        ).to_sse()
                                        event_counter += 1

                                # Check for function response (tool result)
                                elif (
                                    hasattr(part, "function_response")
                                    and part.function_response
                                ):
                                    tool_name = part.function_response.name
                                    tool_response = (
                                        dict(part.function_response.response)
                                        if hasattr(part.function_response, "response")
                                        else {}
                                    )
                                    tool_id = getattr(part.function_response, "id", None)

                                    logger.info(f"✅ Tool response received: {tool_name} (id={tool_id})")

                                    # Extract hook from session state (tools store it there)
                                    # Also try to extract from tool response if present
                                    tool_hook = None
                                    tool_message = None

                                    # First, check if hook is already in session state (set by the tool)
                                    if session and "last_tool_hook" in session.state:
                                        tool_hook = session.state.get("last_tool_hook")

                                    # Also try to extract from tool response JSON if present
                                    if tool_response and "result" in tool_response:
                                        result_str = tool_response.get("result", "")

                                        if isinstance(result_str, str):
                                            try:
                                                # Try to parse as JSON
                                                result_json = json.loads(result_str)

                                                if isinstance(result_json, dict):
                                                    # Extract message if present
                                                    if "message" in result_json:
                                                        tool_message = result_json["message"]
                                                    # Extract hook if present (override session state hook if found)
                                                    if "hook" in result_json:
                                                        tool_hook = result_json["hook"]
                                                        # Store hook for done event (persists across loop iterations)
                                                        tool_hooks_from_stream.append(tool_hook)
                                                        # Also store in session state for backward compatibility
                                                        if session:
                                                            session.state["last_tool_hook"] = tool_hook
                                            except (json.JSONDecodeError, ValueError):
                                                # Not JSON, ignore
                                                pass

                                    # Send single tool_response event with complete message and hook
                                    yield StreamEvent(
                                        event_type="tool_response",
                                        data={
                                            "tool_name": tool_name,
                                            "tool_id": tool_id,
                                            "tool_response": tool_message or "",
                                            "agent": current_agent,
                                            "hook": tool_hook,  # Include hook if present
                                        },
                                        event_id=str(event_counter),
                                    ).to_sse()
                                    event_counter += 1

                                # Stream text content chunks
                                elif hasattr(part, "text") and part.text:
                                    chunk = part.text

                                    # Memory protection: check response size limit
                                    if len(response_text) + len(chunk) > MAX_RESPONSE_SIZE:
                                        if not max_response_reached:
                                            max_response_reached = True
                                            logger.warning(f"Response size limit reached ({MAX_RESPONSE_SIZE} bytes) for session {session_id}")
                                            yield StreamEvent(
                                                event_type="content",
                                                data={
                                                    "chunk": f"\n\n[Response truncated - size limit reached]",
                                                    "accumulated_length": len(response_text),
                                                    "partial": False,
                                                    "agent": current_agent,
                                                    "truncated": True,
                                                },
                                                event_id=str(event_counter),
                                            ).to_sse()
                                            event_counter += 1
                                        continue  # Skip further content accumulation

                                    response_text += chunk

                                    # Check if this is partial (streaming) or complete
                                    is_partial = getattr(event, "partial", False)

                                    yield StreamEvent(
                                        event_type="content",
                                        data={
                                            "chunk": chunk,
                                            "accumulated_length": len(response_text),
                                            "partial": is_partial,
                                            "agent": current_agent,
                                        },
                                        event_id=str(event_counter),
                                    ).to_sse()
                                    event_counter += 1

                                    # Event count protection
                                    if event_counter >= MAX_EVENTS_PER_STREAM:
                                        logger.warning(f"Event limit reached ({MAX_EVENTS_PER_STREAM}) for session {session_id}")
                                        break

                    # Detect state changes
                    if hasattr(event, "actions") and event.actions:
                        if (
                            hasattr(event.actions, "state_delta")
                            and event.actions.state_delta
                        ):
                            yield StreamEvent(
                                event_type="state_change",
                                data={
                                    "state_delta": dict(event.actions.state_delta),
                                    "message": "Session state updated",
                                    "agent": current_agent,
                                },
                                event_id=str(event_counter),
                            ).to_sse()
                            event_counter += 1

                        # Detect artifact changes
                        if (
                            hasattr(event.actions, "artifact_delta")
                            and event.actions.artifact_delta
                        ):
                            yield StreamEvent(
                                event_type="artifact_change",
                                data={
                                    "artifact_delta": {
                                        k: str(v)
                                        for k, v in dict(
                                            event.actions.artifact_delta
                                        ).items()
                                    },
                                    "message": "Artifacts updated",
                                    "agent": current_agent,
                                },
                                event_id=str(event_counter),
                            ).to_sse()
                            event_counter += 1

                        # Detect agent transfer
                        if (
                            hasattr(event.actions, "transfer_to_agent")
                            and event.actions.transfer_to_agent
                        ):
                            yield StreamEvent(
                                event_type="agent_transfer",
                                data={
                                    "from_agent": current_agent,
                                    "to_agent": event.actions.transfer_to_agent,
                                    "message": f"Transferring to agent: {event.actions.transfer_to_agent}",
                                },
                                event_id=str(event_counter),
                            ).to_sse()
                            event_counter += 1

                    # Allow other tasks to run
                    await asyncio.sleep(0)

            except Exception as adk_error:
                # Handle ADK-specific errors during event processing
                error_occurred = True
                error_details = {
                    "error": str(adk_error),
                    "error_type": type(adk_error).__name__,
                    "message": "Error in ADK agent processing",
                    "context": "ADK event processing loop",
                }

                logger.error(f"ADK event processing error: {adk_error}", exc_info=True)

                yield StreamEvent(
                    event_type="error",
                    data=error_details,
                    event_id=str(event_counter),
                ).to_sse()
                event_counter += 1

            # Get final session state and save
            # NOTE: With write-behind caching, state changes (including hooks) are queued in the cache
            # as pending_state_delta. We need to merge these with the session state to get the complete
            # state including hooks that were set during the stream.
            try:
                final_session_state = dict(session.state) if session else {}

                # Merge pending state delta from write-behind cache
                # This includes hooks and other state changes that haven't been persisted yet
                if session_technical_id and hasattr(
                    agent_wrapper.runner.session_service, "get_pending_state_delta"
                ):
                    pending_delta = agent_wrapper.runner.session_service.get_pending_state_delta(
                        session_technical_id
                    )
                    if pending_delta:
                        logger.info(f"📦 Merging {len(pending_delta)} pending state changes")
                        final_session_state.update(pending_delta)

                if conversation_id and final_session_state:
                    await agent_wrapper._save_session_state(
                        conversation_id, final_session_state
                    )
            except Exception as session_error:
                logger.warning(f"Error extracting session state: {session_error}")
                final_session_state = {}
                # Don't set error_occurred here as this is not critical for the user

            # Extract UI functions
            ui_functions = final_session_state.get("ui_functions", [])

            # Extract repository info from tool_context.state (set by build agent tools)
            repository_info = None
            if (
                final_session_state.get("repository_name")
                and final_session_state.get("repository_owner")
                and final_session_state.get("branch_name")
            ):
                repository_info = {
                    "repository_name": final_session_state.get("repository_name"),
                    "repository_owner": final_session_state.get("repository_owner"),
                    "repository_branch": final_session_state.get("branch_name"),
                }
                logger.info(f"📦 Repository info from session state: {repository_info}")

            # Extract build task ID from tool_context.state (set by build agent)
            build_task_id = final_session_state.get("build_task_id")
            if build_task_id:
                logger.info(f"📋 Build task ID from session state: {build_task_id}")

            # Extract hook from tool_context.state (set by tools like commit_and_push_changes)
            tool_hook = final_session_state.get("last_tool_hook")
            if tool_hook:
                logger.info(f"🎣 Hook from tool in session state: {tool_hook.get('type', 'unknown')}")

        except Exception as e:
            error_occurred = True

            # Create detailed error information
            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "An error occurred during processing",
            }

            # Add more context for specific error types
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                error_details["status_code"] = e.response.status_code
            if hasattr(e, 'code'):
                error_details["error_code"] = e.code

            logger.error(f"Error during streaming: {e}", exc_info=True)

            # Send error event with detailed information
            yield StreamEvent(
                event_type="error",
                data=error_details,
                event_id=str(event_counter),
            ).to_sse()
            event_counter += 1

        finally:
            # ALWAYS send 'done' event - whether success, error, or early exit
            # This ensures the UI never hangs waiting for completion

            # Get final session state for done event
            final_session_state = {}
            ui_functions = []
            repository_info = None
            build_task_id = None
            tool_hook = None

            try:
                if session:
                    final_session_state = dict(session.state)

                    # Merge pending state delta from write-behind cache
                    # This includes hooks and other state changes that haven't been persisted yet
                    if session_technical_id and hasattr(
                        agent_wrapper.runner.session_service, "get_pending_state_delta"
                    ):
                        pending_delta = agent_wrapper.runner.session_service.get_pending_state_delta(
                            session_technical_id
                        )
                        if pending_delta:
                            logger.info(f"🎣 Merging {len(pending_delta)} pending state changes for hooks")
                            final_session_state.update(pending_delta)

                    ui_functions = final_session_state.get("ui_functions", [])

                    # Extract repository info
                    if (
                        final_session_state.get("repository_name")
                        and final_session_state.get("repository_owner")
                        and final_session_state.get("branch_name")
                    ):
                        repository_info = {
                            "repository_name": final_session_state.get(
                                "repository_name"
                            ),
                            "repository_owner": final_session_state.get(
                                "repository_owner"
                            ),
                            "repository_branch": final_session_state.get("branch_name"),
                        }

                    # Extract build task ID
                    build_task_id = final_session_state.get("build_task_id")

                    # Extract hook from tools
                    tool_hook = final_session_state.get("last_tool_hook")

                    # Normalize hook to fix serialization issues
                    if tool_hook:
                        tool_hook = normalize_hook(tool_hook)

                    # Debug: Log hook structure after normalization
                    if tool_hook:
                        logger.info(f"🎣 Hook after normalization - type: {type(tool_hook)}")
                        logger.info(f"🎣 Hook data: {tool_hook}")
                        if isinstance(tool_hook, dict) and "data" in tool_hook:
                            logger.info(f"🎣 Hook.data type: {type(tool_hook['data'])}")
                            logger.info(f"🎣 Hook.data: {tool_hook['data']}")
                            if "options" in tool_hook["data"]:
                                logger.info(f"🎣 Hook.data.options type: {type(tool_hook['data']['options'])}")
                                logger.info(f"🎣 Hook.data.options: {tool_hook['data']['options']}")
            except Exception as state_error:
                logger.warning(f"Could not extract final session state: {state_error}")

            # Extract hook message from response if hook exists
            # The response field should contain the full accumulated content
            # The hook_message field should contain the hook UI message
            hook_message = None

            if tool_hook and tool_hook.get("data", {}).get("question"):
                # If there's a hook with a question, extract it for the hook_message field
                hook_question = tool_hook["data"]["question"]
                # Look for the hook question in the response
                if hook_question in response_text:
                    # Split at the hook question - keep everything after it as hook message
                    parts = response_text.split(hook_question, 1)
                    hook_message = hook_question + (parts[1] if len(parts) > 1 else "")
                else:
                    # Hook question not in response - construct hook_message from hook data
                    # This handles cases where the hook is generated by tools but not in the response text
                    hook_message = hook_question
                    # If there are additional hook data fields, add them to the message
                    if tool_hook.get("data", {}).get("options"):
                        hook_message += "\n\nPlease select your choice(s) using the options below."

            # Send done event
            done_message = (
                "Stream ended due to error"
                if error_occurred
                else "Agent completed processing"
            )

            # Get hook from collected hooks during stream ONLY
            # Do NOT fall back to session state - that would be a stale hook from a previous stream
            final_hook = None
            if tool_hooks_from_stream:
                # Use the last hook from the stream (most recent)
                final_hook = tool_hooks_from_stream[-1]
                logger.info(f"🎣 Using hook from stream (collected {len(tool_hooks_from_stream)} hooks)")

            done_data = {
                "message": done_message,
                "response": response_text,  # Full accumulated content
                "hook_message": hook_message,  # Separate hook message if exists
                "adk_session_id": session_technical_id,
                "ui_functions": ui_functions,
                "repository_info": repository_info,
                "build_task_id": build_task_id,
                "hook": final_hook,  # Include hook from tools or session state
                "hooks": tool_hooks_from_stream if tool_hooks_from_stream else None,  # All hooks
                "total_events": event_counter,
            }

            if error_occurred:
                # Include detailed error info if there was an error
                if error_details:
                    done_data.update(error_details)
                    # Add additional context to the done event
                    done_data["error_context"] = {
                        "events_processed": events_processed,
                        "response_length": len(response_text),
                        "event_count": event_counter,
                        "session_id": session_technical_id,
                    }
                else:
                    done_data["error"] = "An error occurred during processing"

            yield StreamEvent(
                event_type="done",
                data=done_data,
                event_id=str(event_counter),
            ).to_sse()

            # Clear the hook from session state after sending it in done event
            # This ensures the next stream doesn't receive stale hooks from previous runs
            # Streams should be stateless - each stream should start fresh
            if session and "last_tool_hook" in session.state:
                del session.state["last_tool_hook"]
                logger.info("🧹 Cleared last_tool_hook from session state after done event")

                # Persist the cleared state to database via an event
                # This ensures the hook doesn't persist to the next stream
                try:
                    event = Event(
                        invocation_id=f"cleanup-{session_technical_id}",
                        author="system",
                        actions=EventActions(state_delta={"last_tool_hook": None}),
                    )
                    await agent_wrapper.runner.session_service.append_event(
                        session=session, event=event
                    )
                    logger.info("✅ Persisted hook cleanup to session via event")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Failed to persist hook cleanup: {cleanup_error}")

            # PERFORMANCE OPTIMIZATION: Flush all pending events in a single batch
            # This is the key optimization - instead of persisting each event individually
            # during the stream (which caused ~100 HTTP calls), we batch them and persist once here.
            if session_technical_id and hasattr(
                agent_wrapper.runner.session_service, "flush_session"
            ):
                try:
                    pending_count = agent_wrapper.runner.session_service.get_pending_event_count(
                        session_technical_id
                    )
                    if pending_count > 0:
                        logger.info(
                            f"🔄 Flushing {pending_count} pending events for session {session_technical_id}"
                        )
                        flush_success = await agent_wrapper.runner.session_service.flush_session(
                            session_technical_id
                        )
                        if flush_success:
                            logger.info(
                                f"✅ Successfully flushed session {session_technical_id}"
                            )
                        else:
                            logger.warning(
                                f"⚠️ Failed to flush session {session_technical_id}"
                            )
                except Exception as flush_error:
                    logger.error(f"❌ Error flushing session: {flush_error}")

            # Ensure stream is properly closed
            logger.info(
                f"Stream closed for session {session_id}, error_occurred={error_occurred}, events_processed={events_processed}"
            )

    @staticmethod
    async def stream_progress_updates(
        task_id: str,
        task_service: Any,
        poll_interval: int = 3,
    ) -> AsyncGenerator[str, None]:
        """
        Stream background task progress updates.

        Polls the BackgroundTask entity and streams progress events.
        Sends heartbeat comments every poll_interval to prevent client timeouts.

        Args:
            task_id: Background task ID
            task_service: Task service instance
            poll_interval: Seconds between polls (default: 3)

        Yields:
            SSE-formatted progress events
        """
        event_counter = 0
        last_progress = -1
        last_heartbeat = asyncio.get_event_loop().time()
        heartbeat_interval = 20  # Send heartbeat every 20 seconds

        try:
            yield StreamEvent(
                event_type="start",
                data={"message": "Monitoring task progress", "task_id": task_id},
                event_id=str(event_counter),
            ).to_sse()
            event_counter += 1

            while True:
                # Get task status
                task = await task_service.get_task(task_id)

                if not task:
                    yield StreamEvent(
                        event_type="error",
                        data={"error": "Task not found", "task_id": task_id},
                        event_id=str(event_counter),
                    ).to_sse()
                    break

                # Send progress update if changed
                if task.progress != last_progress:
                    last_progress = task.progress
                    yield StreamEvent(
                        event_type="progress",
                        data={
                            "task_id": task_id,
                            "progress": task.progress,
                            "status": task.status,
                            "statistics": task.statistics or {},
                        },
                        event_id=str(event_counter),
                    ).to_sse()
                    event_counter += 1
                    last_heartbeat = asyncio.get_event_loop().time()
                else:
                    # Send heartbeat if no progress update and enough time has passed
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        # Send SSE comment as heartbeat (keeps connection alive)
                        yield f": heartbeat {int(current_time)}\n\n"
                        last_heartbeat = current_time

                # Check if task is complete
                if task.status in ["completed", "failed", "cancelled"]:
                    yield StreamEvent(
                        event_type="done",
                        data={
                            "task_id": task_id,
                            "status": task.status,
                            "result": task.result,
                            "error": task.error,
                        },
                        event_id=str(event_counter),
                    ).to_sse()
                    break

                # Wait before next poll
                await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error streaming task progress: {e}", exc_info=True)
            yield StreamEvent(
                event_type="error",
                data={"error": str(e), "task_id": task_id},
                event_id=str(event_counter),
            ).to_sse()
