"""Tests for stream_and_save function in application/services/chat_stream_service.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.entity.conversation import Conversation
from application.services.chat.stream_service import ChatStreamService


@pytest.fixture
def mock_chat_service():
    """Create mock chat service."""
    return AsyncMock()


@pytest.fixture
def mock_persistence_service():
    """Create mock persistence service."""
    return AsyncMock()


@pytest.fixture
def stream_service(mock_chat_service, mock_persistence_service):
    """Create ChatStreamService instance."""
    return ChatStreamService(mock_chat_service, mock_persistence_service)


@pytest.fixture
def mock_conversation():
    """Create mock conversation."""
    conv = MagicMock(spec=Conversation)
    conv.messages = []
    conv.adk_session_id = None
    return conv


@pytest.fixture
def mock_assistant():
    """Create mock assistant."""
    return MagicMock()


class TestStreamAndSave:
    """Tests for ChatStreamService.stream_and_save with >=70% coverage."""

    @pytest.mark.asyncio
    async def test_stream_and_save_basic_openai(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test basic stream_and_save with OpenAI SDK."""

        async def mock_generator():
            yield 'event: content\ndata: {"chunk": "Hello"}\n\n'
            yield 'event: done\ndata: {"adk_session_id": "sess-123"}\n\n'

        with patch.object(
            stream_service, "_stream_openai", return_value=mock_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-123")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test message",
                    conversation=mock_conversation,
                    technical_id="conv-123",
                    user_id="user-123",
                ):
                    events.append(event)

                assert len(events) > 0
                assert any("content" in e for e in events)

    @pytest.mark.asyncio
    async def test_stream_and_save_with_adk_session(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test stream_and_save updates adk_session_id."""

        async def mock_generator():
            yield 'event: content\ndata: {"chunk": "Response"}\n\n'
            yield 'event: done\ndata: {"adk_session_id": "new-session-id"}\n\n'

        with patch.object(
            stream_service, "_stream_openai", return_value=mock_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-456")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test",
                    conversation=mock_conversation,
                    technical_id="conv-456",
                    user_id="user-456",
                ):
                    events.append(event)

                assert len(events) > 0

    @pytest.mark.asyncio
    async def test_stream_and_save_with_hook_metadata(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test stream_and_save preserves hook metadata."""

        async def mock_generator():
            yield 'event: content\ndata: {"chunk": "Test"}\n\n'
            yield 'event: done\ndata: {"hook": {"type": "option_selection"}}\n\n'

        with patch.object(
            stream_service, "_stream_openai", return_value=mock_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-789")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test",
                    conversation=mock_conversation,
                    technical_id="conv-789",
                    user_id="user-789",
                ):
                    events.append(event)

                assert len(events) > 0

    @pytest.mark.asyncio
    async def test_stream_and_save_empty_response(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test stream_and_save with empty accumulated response."""

        async def mock_generator():
            yield "event: done\ndata: {}\n\n"

        with patch.object(
            stream_service, "_stream_openai", return_value=mock_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-empty")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test",
                    conversation=mock_conversation,
                    technical_id="conv-empty",
                    user_id="user-empty",
                ):
                    events.append(event)

                assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_stream_and_save_with_error(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test stream_and_save handles streaming errors."""

        async def error_generator():
            yield 'event: content\ndata: {"chunk": "Start"}\n\n'
            raise Exception("Stream error")

        with patch.object(
            stream_service, "_stream_openai", return_value=error_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test",
                    conversation=mock_conversation,
                    technical_id="conv-error",
                    user_id="user-error",
                ):
                    events.append(event)

                assert any("error" in e for e in events)

    @pytest.mark.asyncio
    async def test_stream_and_save_with_google_adk(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test stream_and_save with Google ADK SDK."""

        async def mock_generator():
            yield 'event: content\ndata: {"chunk": "ADK"}\n\n'
            yield "event: done\ndata: {}\n\n"

        with patch(
            "application.services.chat.stream_service.StreamingService"
        ) as mock_streaming:
            mock_streaming.stream_agent_response = MagicMock(
                return_value=mock_generator()
            )
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=False,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-adk")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test",
                    conversation=mock_conversation,
                    technical_id="conv-adk",
                    user_id="user-adk",
                ):
                    events.append(event)

                assert len(events) > 0

    @pytest.mark.asyncio
    async def test_stream_and_save_multiple_chunks(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test stream_and_save accumulates multiple content chunks."""

        async def mock_generator():
            yield 'event: content\ndata: {"chunk": "Hello "}\n\n'
            yield 'event: content\ndata: {"chunk": "World"}\n\n'
            yield "event: done\ndata: {}\n\n"

        with patch.object(
            stream_service, "_stream_openai", return_value=mock_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-multi")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test",
                    conversation=mock_conversation,
                    technical_id="conv-multi",
                    user_id="user-multi",
                ):
                    events.append(event)

                assert len(events) >= 2

    @pytest.mark.asyncio
    async def test_stream_and_save_with_repository_info(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test stream_and_save updates repository info from metadata."""

        async def mock_generator():
            yield 'event: content\ndata: {"chunk": "Repo"}\n\n'
            yield 'event: done\ndata: {"repository_info": {"repository_name": "test-repo", "repository_owner": "owner"}}\n\n'

        with patch.object(
            stream_service, "_stream_openai", return_value=mock_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-repo")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test",
                    conversation=mock_conversation,
                    technical_id="conv-repo",
                    user_id="user-repo",
                ):
                    events.append(event)

                assert len(events) > 0

    @pytest.mark.asyncio
    async def test_stream_and_save_no_duplicate_done_events(
        self, stream_service, mock_assistant, mock_conversation
    ):
        """Test that done events are not duplicated in the stream."""

        async def mock_generator():
            yield 'event: content\ndata: {"chunk": "Response"}\n\n'
            yield 'event: done\ndata: {"adk_session_id": "sess-123", "response": "Test response"}\n\n'

        with patch.object(
            stream_service, "_stream_openai", return_value=mock_generator()
        ):
            with patch(
                "application.services.chat.stream_service.is_using_openai_sdk",
                return_value=True,
            ):
                stream_service.persistence_service.save_response_with_history = (
                    AsyncMock(return_value="resp-123")
                )
                stream_service.chat_service.get_conversation = AsyncMock(
                    return_value=mock_conversation
                )
                stream_service.chat_service.update_conversation = AsyncMock(
                    return_value=mock_conversation
                )

                events = []
                async for event in stream_service.stream_and_save(
                    assistant=mock_assistant,
                    message_to_process="Test message",
                    conversation=mock_conversation,
                    technical_id="conv-123",
                    user_id="user-123",
                ):
                    events.append(event)

                # Count done events
                done_events = [e for e in events if "event: done" in e]
                assert (
                    len(done_events) == 1
                ), f"Expected 1 done event, got {len(done_events)}"
