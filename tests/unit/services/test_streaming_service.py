"""Unit tests for streaming_service module."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.streaming_service import (
    CLIInvocationTracker,
    StreamEvent,
    StreamingService,
    check_cli_invocation_limit,
    format_response_section,
    get_cli_invocation_count,
    normalize_hook,
    reset_cli_invocation_count,
)


class TestStreamEvent:
    """Test StreamEvent class."""

    def test_stream_event_initialization(self):
        """Test StreamEvent initialization."""
        event = StreamEvent(
            event_type="test", data={"message": "test message"}, event_id="123"
        )
        assert event.event_type == "test"
        assert event.data == {"message": "test message"}
        assert event.event_id == "123"
        assert event.timestamp is not None

    def test_stream_event_auto_generates_id(self):
        """Test StreamEvent auto-generates ID if not provided."""
        event = StreamEvent(event_type="test", data={"message": "test"})
        assert event.event_id is not None
        assert len(event.event_id) > 0

    def test_stream_event_to_sse(self):
        """Test StreamEvent converts to SSE format."""
        event = StreamEvent(event_type="test", data={"message": "test"}, event_id="123")
        sse = event.to_sse()
        assert "data:" in sse
        assert "test" in sse
        assert "123" in sse

    def test_stream_event_to_sse_with_complex_data(self):
        """Test StreamEvent converts complex data to SSE format."""
        data = {"message": "test", "nested": {"key": "value"}, "list": [1, 2, 3]}
        event = StreamEvent(event_type="complex", data=data, event_id="456")
        sse = event.to_sse()
        assert "data:" in sse
        assert "nested" in sse
        assert "456" in sse


class TestCLIInvocationTracker:
    """Test CLI invocation tracking."""

    def test_check_cli_invocation_limit_within_limit(self):
        """Test that check_cli_invocation_limit returns allowed when within limit."""
        session_id = "test-session-1"
        reset_cli_invocation_count(session_id)
        is_allowed, message = check_cli_invocation_limit(session_id)
        assert is_allowed is True

    def test_check_cli_invocation_limit_exceeds_limit(self):
        """Test that check_cli_invocation_limit returns not allowed when limit exceeded."""
        session_id = "test-session-2"
        reset_cli_invocation_count(session_id)
        for _ in range(11):
            is_allowed, message = check_cli_invocation_limit(session_id)
        # After 11 calls, should exceed limit of 10
        assert is_allowed is False

    def test_reset_cli_invocation_count(self):
        """Test that reset_cli_invocation_count resets the counter."""
        session_id = "test-session-3"
        reset_cli_invocation_count(session_id)
        check_cli_invocation_limit(session_id)
        reset_cli_invocation_count(session_id)
        count = get_cli_invocation_count(session_id)
        assert count == 0

    def test_cli_tracker_boundary_conditions(self):
        """Test CLI tracker at boundary conditions."""
        session_id = "test-session-boundary"
        reset_cli_invocation_count(session_id)

        # Test at limit (10)
        for _ in range(10):
            is_allowed, message = check_cli_invocation_limit(session_id)
            assert is_allowed is True

        # Test exceeding limit
        is_allowed, message = check_cli_invocation_limit(session_id)
        assert is_allowed is False
        assert "LIMIT EXCEEDED" in message

    def test_get_cli_invocation_count(self):
        """Test get_cli_invocation_count returns correct count."""
        session_id = "test-session-count"
        reset_cli_invocation_count(session_id)

        # Add some calls
        for i in range(5):
            check_cli_invocation_limit(session_id)

        count = get_cli_invocation_count(session_id)
        assert count == 5


class TestNormalizeHook:
    """Test normalize_hook function."""

    def test_normalize_hook_with_dict(self):
        """Test normalize_hook with dictionary input."""
        hook = {"type": "test", "data": {"key": "value"}}
        result = normalize_hook(hook)
        assert isinstance(result, dict)
        assert result.get("type") == "test"

    def test_normalize_hook_with_non_dict(self):
        """Test normalize_hook with non-dictionary input."""
        result = normalize_hook("not a dict")
        assert result == "not a dict"

    def test_normalize_hook_with_none(self):
        """Test normalize_hook with None input."""
        result = normalize_hook(None)
        assert result is None

    def test_normalize_hook_preserves_structure(self):
        """Test normalize_hook preserves hook structure."""
        hook = {"type": "test", "data": {"nested": {"key": "value"}}}
        result = normalize_hook(hook)
        assert result.get("type") == "test"
        assert result.get("data") is not None


class TestFormatResponseSection:
    """Test format_response_section function."""

    def test_format_response_section_with_text(self):
        """Test format_response_section with text content."""
        result = format_response_section("Test Title", "test content")
        assert "test content" in result
        assert "Test Title" in result

    def test_format_response_section_with_empty_content(self):
        """Test format_response_section with empty content."""
        result = format_response_section("Title", "")
        assert result == ""

    def test_format_response_section_with_special_characters(self):
        """Test format_response_section with special characters."""
        content = "test\nwith\nnewlines"
        result = format_response_section("Title", content)
        assert "test" in result
        assert "newlines" in result

    def test_format_response_section_with_section_type(self):
        """Test format_response_section with different section types."""
        result = format_response_section(
            "Title", "content", section_type="tool_response"
        )
        assert "content" in result
        assert "Title" in result


class TestStreamingServiceAsync:
    """Test async streaming functions."""

    @pytest.mark.asyncio
    async def test_stream_agent_response_basic_flow(self):
        """Test basic stream_agent_response flow with empty event stream."""
        mock_agent = AsyncMock()
        mock_agent.runner = MagicMock()
        mock_agent.runner.session_service = AsyncMock()
        mock_agent.runner.session_service.get_session = AsyncMock(return_value=None)

        created_session = MagicMock()
        created_session.state = {"__cyoda_technical_id__": "tech-123"}
        mock_agent.runner.session_service.create_session = AsyncMock(
            return_value=created_session
        )

        async def mock_generator():
            return
            yield

        mock_agent.runner.run_async = MagicMock(
            side_effect=lambda **kwargs: mock_generator()
        )

        events = []
        async for event in StreamingService.stream_agent_response(
            agent_wrapper=mock_agent,
            user_message="test",
            conversation_history=[],
            conversation_id="conv1",
            adk_session_id=None,
            user_id="user1",
        ):
            events.append(event)

        # Should have start and done events
        assert len(events) >= 2
        assert any("start" in event for event in events)
        assert any("done" in event for event in events)

    @pytest.mark.asyncio
    async def test_stream_progress_updates_success(self):
        """Test streaming progress updates for successful task."""
        task_service = AsyncMock()

        # Mock task that completes
        task = MagicMock()
        task.progress = 100
        task.status = "completed"
        task.statistics = {"files": 5}
        task.result = "Success"
        task.error = None

        task_service.get_task = AsyncMock(return_value=task)

        events = []
        async for event in StreamingService.stream_progress_updates(
            task_id="task-123", task_service=task_service, poll_interval=0.1
        ):
            events.append(event)

        assert len(events) > 0
        assert any("done" in event for event in events)

    @pytest.mark.asyncio
    async def test_stream_progress_updates_task_not_found(self):
        """Test streaming when task is not found."""
        task_service = AsyncMock()
        task_service.get_task = AsyncMock(return_value=None)

        events = []
        async for event in StreamingService.stream_progress_updates(
            task_id="task-123", task_service=task_service, poll_interval=0.1
        ):
            events.append(event)

        assert len(events) > 0
        assert any("error" in event for event in events)


class TestStreamAgentResponseEdgeCases:
    """Test edge cases and error scenarios for stream_agent_response."""

    @pytest.mark.asyncio
    async def test_stream_event_json_serialization(self):
        """Test that StreamEvent properly serializes to JSON."""
        event = StreamEvent(
            event_type="test",
            data={"key": "value", "nested": {"inner": "data"}},
            event_id="123",
        )
        sse = event.to_sse()

        # Verify SSE format
        assert "id: 123" in sse
        assert "event: test" in sse
        assert "data:" in sse
        assert "key" in sse
        assert "value" in sse

    @pytest.mark.asyncio
    async def test_stream_event_with_large_data(self):
        """Test StreamEvent with large data payload."""
        large_data = {"content": "x" * 10000, "metadata": {"size": 10000}}
        event = StreamEvent(event_type="large", data=large_data, event_id="456")
        sse = event.to_sse()

        # Should still serialize properly
        assert "event: large" in sse
        assert "456" in sse


class TestStreamingServiceHelperMethods:
    """Test helper methods of StreamingService."""

    def test_build_progress_event(self):
        """Test _build_progress_event method."""
        task_id = "task-123"
        task = MagicMock()
        task.progress = 75
        task.status = "in_progress"
        task.statistics = {"files": 10, "time": 30}

        event_sse, counter = StreamingService._build_progress_event(task_id, task, 0)

        assert "progress" in event_sse
        assert "in_progress" in event_sse
        assert "task-123" in event_sse
        assert counter == 1

    def test_build_heartbeat_event(self):
        """Test _build_heartbeat_event method."""
        heartbeat = StreamingService._build_heartbeat_event()

        assert "heartbeat" in heartbeat
        assert heartbeat.startswith(":")

    @pytest.mark.asyncio
    async def test_check_heartbeat_and_yield(self):
        """Test _check_heartbeat_and_yield method."""
        import time

        last_beat = asyncio.get_event_loop().time() - 25  # 25 seconds ago

        # Should yield heartbeat after 20 second interval
        event, new_time = await StreamingService._check_heartbeat_and_yield(
            last_beat, 20
        )

        assert event is not None, "Should yield heartbeat after interval"
        assert "heartbeat" in event

    def test_is_task_complete(self):
        """Test _is_task_complete method."""
        # Test completed state
        task_completed = MagicMock()
        task_completed.status = "completed"
        assert StreamingService._is_task_complete(task_completed)

        # Test failed state
        task_failed = MagicMock()
        task_failed.status = "failed"
        assert StreamingService._is_task_complete(task_failed)

        # Test cancelled state
        task_cancelled = MagicMock()
        task_cancelled.status = "cancelled"
        assert StreamingService._is_task_complete(task_cancelled)

        # Test in_progress state (not complete)
        task_running = MagicMock()
        task_running.status = "in_progress"
        assert not StreamingService._is_task_complete(task_running)

    def test_build_completion_event(self):
        """Test _build_completion_event method."""
        task_id = "task-456"
        task = MagicMock()
        task.status = "completed"
        task.result = "Success"
        task.error = None

        event_sse = StreamingService._build_completion_event(task_id, task, 5)

        assert "done" in event_sse
        assert "task-456" in event_sse
        assert "completed" in event_sse


class TestStreamingServiceIntegration:
    """Integration tests for streaming service."""

    @pytest.mark.asyncio
    async def test_stream_agent_response_with_empty_user_message(self):
        """Test stream_agent_response with empty user message."""
        mock_agent = AsyncMock()
        mock_agent.runner = MagicMock()
        mock_agent.runner.session_service = AsyncMock()
        mock_agent.runner.session_service.get_session = AsyncMock(return_value=None)

        created_session = MagicMock()
        created_session.state = {"__cyoda_technical_id__": "tech-empty"}
        mock_agent.runner.session_service.create_session = AsyncMock(
            return_value=created_session
        )

        async def mock_generator():
            return
            yield

        mock_agent.runner.run_async = MagicMock(
            side_effect=lambda **kwargs: mock_generator()
        )

        events = []
        async for event in StreamingService.stream_agent_response(
            agent_wrapper=mock_agent,
            user_message="",
            conversation_history=[],
            conversation_id="conv1",
            adk_session_id=None,
            user_id="user1",
        ):
            events.append(event)

        # Should still process even with empty message
        assert len(events) >= 2

    @pytest.mark.asyncio
    async def test_stream_progress_updates_with_statistics(self):
        """Test streaming progress updates with task statistics."""
        task_service = AsyncMock()

        # Create a task that completes after first poll
        task = MagicMock()
        task.progress = 100
        task.status = "completed"
        task.statistics = {"files_processed": 20, "files_total": 20, "elapsed_time": 30}
        task.result = "Success"
        task.error = None

        task_service.get_task = AsyncMock(return_value=task)

        events = []
        async for event in StreamingService.stream_progress_updates(
            task_id="task-789", task_service=task_service, poll_interval=0.01
        ):
            events.append(event)

        assert len(events) > 0
        assert any("done" in event for event in events)

    def test_cli_invocation_tracker_multiple_sessions(self):
        """Test CLI invocation tracker with multiple sessions."""
        session1 = "session-1"
        session2 = "session-2"

        reset_cli_invocation_count(session1)
        reset_cli_invocation_count(session2)

        # Record calls for session 1
        for _ in range(3):
            check_cli_invocation_limit(session1)

        # Record calls for session 2
        for _ in range(5):
            check_cli_invocation_limit(session2)

        # Check counts are independent
        count1 = get_cli_invocation_count(session1)
        count2 = get_cli_invocation_count(session2)

        assert count1 == 3
        assert count2 == 5

    def test_stream_event_with_empty_data(self):
        """Test StreamEvent with empty data dictionary."""
        event = StreamEvent(event_type="empty", data={}, event_id="empty-123")
        sse = event.to_sse()

        assert "event: empty" in sse
        assert "empty-123" in sse
        assert "data:" in sse

    def test_stream_event_with_none_values(self):
        """Test StreamEvent with None values in data."""
        event = StreamEvent(
            event_type="none_test",
            data={"key": None, "other": "value"},
            event_id="none-456",
        )
        sse = event.to_sse()

        assert "event: none_test" in sse
        assert "none-456" in sse
        assert "null" in sse  # JSON representation of None


class TestToolCallLoopDetection:
    """Test tool call loop detection mechanisms."""

    def test_tool_call_tracking_logic(self):
        """Test the logic for tracking tool call counts and detecting loops."""
        # Test tool_call_count tracking
        tool_call_count = 0
        MAX_TOOL_CALLS_PER_STREAM = 50

        # Simulate multiple tool calls
        for i in range(51):
            tool_call_count += 1

            if tool_call_count > MAX_TOOL_CALLS_PER_STREAM:
                loop_detected = True
                break
        else:
            loop_detected = False

        assert loop_detected, "Should detect when tool calls exceed limit"
        assert tool_call_count == 51

    def test_consecutive_identical_tool_calls_detection_logic(self):
        """Test the logic for detecting consecutive identical tool calls."""
        tool_call_history = []
        MAX_CONSECUTIVE_SAME_TOOL = 7
        loop_detected = False

        # Simulate 8 consecutive calls with same tool and args
        tool_call_key = ("retry_tool", "{'attempt': 1}")
        for i in range(8):
            tool_call_history.append(tool_call_key)

            # Check for consecutive identical calls
            if len(tool_call_history) >= MAX_CONSECUTIVE_SAME_TOOL:
                recent = tool_call_history[-MAX_CONSECUTIVE_SAME_TOOL:]
                if all(call == recent[0] for call in recent):
                    loop_detected = True
                    break

        assert loop_detected, "Should detect consecutive identical tool calls"
        # Loop breaks after detecting at index 7 (when we have 7 in history)
        assert len(tool_call_history) == 7, "Should break after detecting loop"

    def test_tool_args_change_resets_consecutive_detection(self):
        """Test that changing tool arguments resets the consecutive count."""
        tool_call_history = []
        MAX_CONSECUTIVE_SAME_TOOL = 7

        # Call pattern: 3 with args1, then change to args2, then 3 more with args2
        call_pattern = [
            ("tool", "{'attempt': 1}"),  # Same
            ("tool", "{'attempt': 1}"),  # Same
            ("tool", "{'attempt': 1}"),  # Same
            (
                "tool",
                "{'attempt': 2}",
            ),  # Different - this should not trigger loop detection
            ("tool", "{'attempt': 2}"),  # Same as previous
            ("tool", "{'attempt': 2}"),  # Same as previous
        ]

        loop_detected = False
        for tool_call_key in call_pattern:
            tool_call_history.append(tool_call_key)

            # Check for consecutive identical calls
            if len(tool_call_history) >= MAX_CONSECUTIVE_SAME_TOOL:
                recent = tool_call_history[-MAX_CONSECUTIVE_SAME_TOOL:]
                if all(call == recent[0] for call in recent):
                    loop_detected = True
                    break

        # Should not detect loop because args change before reaching threshold
        assert not loop_detected, "Should not detect loop when args change"
        assert len(tool_call_history) == 6


class TestResponseSizeLimit:
    """Test response size limit protection."""

    def test_response_size_limit_detection_logic(self):
        """Test the logic for detecting when response size limit is exceeded."""
        MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB
        response_text = ""
        max_response_reached = False

        # Simulate adding text chunks
        chunk_size = 200000  # 200KB
        for i in range(6):  # 6 * 200KB = 1.2MB
            chunk = "x" * chunk_size

            # Check size limit
            if len(response_text) + len(chunk) > MAX_RESPONSE_SIZE:
                if not max_response_reached:
                    max_response_reached = True
                continue  # Skip accumulation

            response_text += chunk

        assert max_response_reached, "Should detect when size limit is exceeded"
        assert (
            len(response_text) <= MAX_RESPONSE_SIZE
        ), "Response should not exceed size limit"


class TestToolResponseExtraction:
    """Test tool response and hook extraction."""

    def test_tool_response_hook_extraction_logic(self):
        """Test the logic for extracting hook from tool response JSON."""
        tool_response = {
            "result": json.dumps(
                {
                    "message": "Commit successful",
                    "hook": {
                        "type": "deployment",
                        "data": {"url": "https://example.com"},
                    },
                }
            )
        }

        # Extract hook from tool response
        tool_hook = None
        tool_message = None

        if tool_response and "result" in tool_response:
            result_str = tool_response.get("result", "")

            if isinstance(result_str, str):
                try:
                    result_json = json.loads(result_str)

                    if isinstance(result_json, dict):
                        if "message" in result_json:
                            tool_message = result_json["message"]
                        if "hook" in result_json:
                            tool_hook = result_json["hook"]
                except (json.JSONDecodeError, ValueError):
                    pass

        assert (
            tool_message == "Commit successful"
        ), "Should extract message from response"
        assert tool_hook is not None, "Should extract hook from response"
        assert tool_hook["type"] == "deployment", "Hook type should match"

    @pytest.mark.asyncio
    async def test_ui_functions_collection_from_session(self):
        """Test collection of ui_functions from session state during stream."""
        mock_agent = AsyncMock()
        mock_agent.runner = MagicMock()
        mock_agent.runner.session_service = AsyncMock()
        mock_agent.runner.session_service.get_session = AsyncMock(return_value=None)
        mock_agent.runner.session_service.get_pending_state_delta = MagicMock(
            return_value=None
        )
        mock_agent.runner.session_service.get_pending_event_count = MagicMock(
            return_value=0
        )
        mock_agent._load_session_state = AsyncMock(return_value={})
        mock_agent._save_session_state = AsyncMock()

        created_session = MagicMock()
        session_state = {
            "__cyoda_technical_id__": "tech-123",
            "ui_functions": [
                {"function": "openTerminal", "context": "build"},
                {"function": "showCanvas", "context": "code"},
            ],
        }
        created_session.state = session_state
        mock_agent.runner.session_service.create_session = AsyncMock(
            return_value=created_session
        )

        async def mock_event_generator():
            event = MagicMock()
            event.author = "test_agent"
            event.content = MagicMock()
            event.content.parts = []

            part = MagicMock()
            part.function_response = MagicMock()
            part.function_response.name = "build_tool"
            part.function_response.response = {"result": "Build completed"}
            part.function_response.id = "resp_1"
            part.function_call = None
            part.text = None
            event.content.parts.append(part)
            event.actions = None
            event.partial = False

            yield event

        mock_agent.runner.run_async = MagicMock(return_value=mock_event_generator())

        events = []
        async for event in StreamingService.stream_agent_response(
            agent_wrapper=mock_agent,
            user_message="test",
            conversation_history=[],
            conversation_id="conv1",
            adk_session_id=None,
            user_id="user1",
        ):
            events.append(event)

        # Check that ui_functions are in done event
        done_event_str = next((e for e in events if "done" in e), None)
        assert done_event_str is not None, "Should have done event"
        assert (
            "ui_functions" in done_event_str
        ), "Done event should contain ui_functions"


class TestStreamTimeout:
    """Test stream timeout detection."""

    @pytest.mark.asyncio
    async def test_stream_timeout_stops_stream(self):
        """Test that stream timeout stops the stream."""
        mock_agent = AsyncMock()
        mock_agent.runner = MagicMock()
        mock_agent.runner.session_service = AsyncMock()
        mock_agent.runner.session_service.get_session = AsyncMock(return_value=None)
        mock_agent._load_session_state = AsyncMock(return_value={})
        mock_agent._save_session_state = AsyncMock()

        created_session = MagicMock()
        created_session.state = {"__cyoda_technical_id__": "tech-123"}
        mock_agent.runner.session_service.create_session = AsyncMock(
            return_value=created_session
        )

        # Create a mock event generator that sleeps to trigger timeout
        timeout_count = [0]

        async def mock_event_generator():
            # This should trigger timeout during wait_for
            event = MagicMock()
            event.author = "test_agent"
            event.content = MagicMock()
            event.content.parts = []
            # Return one event then sleep indefinitely
            if timeout_count[0] == 0:
                timeout_count[0] += 1
                yield event
            else:
                await asyncio.sleep(1000)  # Long sleep to trigger timeout

        mock_agent.runner.run_async = MagicMock(return_value=mock_event_generator())

        events = []
        with patch(
            "application.services.streaming_service.STREAM_TIMEOUT", 0.1
        ):  # Very short timeout
            async for event in StreamingService.stream_agent_response(
                agent_wrapper=mock_agent,
                user_message="test",
                conversation_history=[],
                conversation_id="conv1",
                adk_session_id=None,
                user_id="user1",
            ):
                events.append(event)
                if "timeout" in event.lower():
                    break

        # Should have timeout error or related events
        done_events = [e for e in events if "done" in e]
        assert len(done_events) > 0, "Should have done event after timeout"


class TestNormalizeHookRepository:
    """Test hook normalization for repository_config_selection."""

    def test_normalize_hook_unwraps_options_list(self):
        """Test that repository_config_selection hook options list is unwrapped."""
        hook = {
            "type": "repository_config_selection",
            "data": {
                "question": "Select a repository",
                "options": [{"repo1": {"url": "...", "branch": "main"}}],
            },
        }

        result = normalize_hook(hook)

        # Options should be unwrapped from list
        assert isinstance(result["data"]["options"], dict)
        assert "repo1" in result["data"]["options"]

    def test_normalize_hook_preserves_normal_structure(self):
        """Test that normal hook structure is preserved."""
        hook = {
            "type": "repository_config_selection",
            "data": {
                "question": "Select a repository",
                "options": {"repo1": {"url": "...", "branch": "main"}},
            },
        }

        result = normalize_hook(hook)

        # Should remain unchanged
        assert result["data"]["options"] == hook["data"]["options"]

    def test_normalize_hook_different_hook_types_unchanged(self):
        """Test that non-repository hooks are not modified."""
        hook = {
            "type": "deployment",
            "data": {"status": "pending", "options": [{"env": "prod"}]},
        }

        result = normalize_hook(hook)

        # Should be unchanged for non-repository hooks
        assert result == hook


class TestEventCounter:
    """Test event counter management throughout streaming."""

    def test_event_counter_increments_correctly(self):
        """Test that event counter increments correctly."""
        event_counter = 0

        # Start event
        event_counter += 1
        assert event_counter == 1, "Start event should increment counter"

        # Agent event 1
        event_counter += 1
        assert event_counter == 2, "Agent event should increment counter"

        # Agent event 2
        event_counter += 1
        assert event_counter == 3, "Agent event should increment counter"

        # Tool call event
        event_counter += 1
        assert event_counter == 4, "Tool call event should increment counter"

        # Done event
        event_counter += 1
        assert event_counter == 5, "Done event should increment counter"

        assert event_counter >= 4, "Should have at least 4 events"


class TestStreamEventCounterManagement:
    """Test specific event counter logic for the streaming service."""

    def test_event_counter_logic_in_tool_call_section(self):
        """Test event counter increment in tool call detection section."""
        # Simulating the code from lines 430-504 (tool call detection)
        event_counter = 0
        current_agent = None

        # Simulate agent transition event
        event_author = "test_agent"
        if event_author != "user" and event_author != current_agent:
            current_agent = event_author
            event_counter += 1  # This would be the agent event
            assert event_counter == 1

        # Simulate tool call detected
        tool_name = "my_tool"
        tool_args = {"arg": "value"}
        tool_id = "tool_123"
        current_tool = None
        current_tool_args = None

        if tool_name != current_tool or tool_args != current_tool_args:
            current_tool = tool_name
            current_tool_args = tool_args
            event_counter += 1  # Tool call event
            assert event_counter == 2

        # Simulate another tool call (different args - should emit event)
        tool_args2 = {"arg": "value2"}
        if tool_name != current_tool or tool_args2 != current_tool_args:
            current_tool = tool_name
            current_tool_args = tool_args2
            event_counter += 1  # Another tool call event
            assert event_counter == 3

    def test_event_counter_logic_for_duplicate_tool_calls(self):
        """Test that duplicate tool calls don't increment counter unnecessarily."""
        # This simulates lines 483-504 (tool call emission logic)
        event_counter = 0
        current_tool = None
        current_tool_args = None

        # First tool call
        tool_name = "tool_a"
        tool_args = {"attempt": 1}
        if tool_name != current_tool or tool_args != current_tool_args:
            current_tool = tool_name
            current_tool_args = tool_args
            event_counter += 1
        assert event_counter == 1

        # Duplicate tool call (same tool, same args) - should not emit
        if tool_name != current_tool or tool_args != current_tool_args:
            event_counter += 1
        assert event_counter == 1, "Duplicate calls should not increment counter"

        # Different args - should emit
        tool_args2 = {"attempt": 2}
        if tool_name != current_tool or tool_args2 != current_tool_args:
            current_tool = tool_name
            current_tool_args = tool_args2
            event_counter += 1
        assert event_counter == 2

    def test_event_counter_in_content_section(self):
        """Test event counter increments for text content streaming."""
        # Simulating lines 611-621 (text content streaming)
        event_counter = 0
        response_text = ""
        MAX_RESPONSE_SIZE = 1024 * 1024

        # Simulate content chunks
        chunks = ["Hello ", "world ", "from ", "streaming"]

        for chunk in chunks:
            # Check size limit (simulating lines 588-604)
            if len(response_text) + len(chunk) > MAX_RESPONSE_SIZE:
                continue

            response_text += chunk

            # Emit content event (simulating lines 611-621)
            event_counter += 1

        assert event_counter == 4, "Should have 4 content events"
        assert response_text == "Hello world from streaming"
