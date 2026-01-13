"""Tests for stream event generator."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.entity.conversation import Conversation
from application.routes.chat_endpoints.stream import _create_stream_event_generator


class TestCreateStreamEventGenerator:
    """Tests for _create_stream_event_generator function."""

    @pytest.mark.asyncio
    async def test_event_generator_with_content_events(self):
        """Test event generator processes content events."""
        conversation = Conversation(
            technical_id="conv-123",
            user_id="user-123",
            messages=[],
            adk_session_id=None,
        )

        assistant = MagicMock()

        # Mock streaming generator
        async def mock_stream():
            yield 'event: content\ndata: {"text": "Hello"}\n\n'
            yield 'event: done\ndata: {"response": "Hello"}\n\n'

        with patch(
            "application.routes.chat_endpoints.stream.StreamingService.stream_agent_response",
            return_value=mock_stream(),
        ):
            with patch(
                "application.routes.chat_endpoints.stream.process_content_event"
            ) as mock_process_content:
                with patch(
                    "application.routes.chat_endpoints.stream.process_done_event"
                ) as mock_process_done:
                    with patch(
                        "application.routes.chat_endpoints.stream._finalize_stream",
                        new_callable=AsyncMock,
                    ):
                        mock_process_content.return_value = ("Hello", [])
                        mock_process_done.return_value = (
                            True,
                            "event: done\ndata: {}\n\n",
                            "Hello",
                            None,
                            None,
                            [],
                        )

                        generator = _create_stream_event_generator(
                            technical_id="conv-123",
                            user_id="user-123",
                            conversation=conversation,
                            assistant=assistant,
                            message_to_process="Test message",
                        )

                        events = []
                        async for event in generator:
                            events.append(event)

                        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_event_generator_handles_error(self):
        """Test event generator handles streaming errors."""
        conversation = Conversation(
            technical_id="conv-123",
            user_id="user-123",
            messages=[],
            adk_session_id=None,
        )

        assistant = MagicMock()

        # Mock streaming generator that raises error
        async def mock_stream():
            raise ValueError("Stream error")
            yield  # Make it a generator

        with patch(
            "application.routes.chat_endpoints.stream.StreamingService.stream_agent_response",
            return_value=mock_stream(),
        ):
            with patch(
                "application.routes.chat_endpoints.stream._finalize_stream",
                new_callable=AsyncMock,
            ):
                generator = _create_stream_event_generator(
                    technical_id="conv-123",
                    user_id="user-123",
                    conversation=conversation,
                    assistant=assistant,
                    message_to_process="Test message",
                )

                events = []
                async for event in generator:
                    events.append(event)

                # Should have error event
                assert any("error" in event for event in events)

    @pytest.mark.asyncio
    async def test_event_generator_with_adk_session(self):
        """Test event generator with existing ADK session."""
        conversation = Conversation(
            technical_id="conv-123",
            user_id="user-123",
            messages=[],
            adk_session_id="session-456",
        )

        assistant = MagicMock()

        async def mock_stream():
            yield 'event: done\ndata: {"response": "Test"}\n\n'

        with patch(
            "application.routes.chat_endpoints.stream.StreamingService.stream_agent_response",
            return_value=mock_stream(),
        ):
            with patch(
                "application.routes.chat_endpoints.stream.process_done_event"
            ) as mock_process_done:
                with patch(
                    "application.routes.chat_endpoints.stream._finalize_stream",
                    new_callable=AsyncMock,
                ):
                    mock_process_done.return_value = (
                        True,
                        "event: done\ndata: {}\n\n",
                        "Test",
                        None,
                        None,
                        [],
                    )

                    generator = _create_stream_event_generator(
                        technical_id="conv-123",
                        user_id="user-123",
                        conversation=conversation,
                        assistant=assistant,
                        message_to_process="Test message",
                    )

                    events = []
                    async for event in generator:
                        events.append(event)

                    assert len(events) > 0

    @pytest.mark.asyncio
    async def test_event_generator_finalizes_on_completion(self):
        """Test event generator calls finalize on completion."""
        conversation = Conversation(
            technical_id="conv-123",
            user_id="user-123",
            messages=[],
            adk_session_id=None,
        )

        assistant = MagicMock()

        async def mock_stream():
            yield 'event: done\ndata: {"response": "Done"}\n\n'

        with patch(
            "application.routes.chat_endpoints.stream.StreamingService.stream_agent_response",
            return_value=mock_stream(),
        ):
            with patch(
                "application.routes.chat_endpoints.stream.process_done_event"
            ) as mock_process_done:
                with patch(
                    "application.routes.chat_endpoints.stream._finalize_stream",
                    new_callable=AsyncMock,
                ) as mock_finalize:
                    mock_process_done.return_value = (
                        True,
                        "event: done\ndata: {}\n\n",
                        "Done",
                        None,
                        None,
                        [],
                    )

                    generator = _create_stream_event_generator(
                        technical_id="conv-123",
                        user_id="user-123",
                        conversation=conversation,
                        assistant=assistant,
                        message_to_process="Test message",
                    )

                    async for _ in generator:
                        pass

                    # Verify finalize was called
                    assert mock_finalize.called
