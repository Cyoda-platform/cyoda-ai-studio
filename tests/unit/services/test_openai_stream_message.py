"""Tests for OpenAIAssistantWrapper.stream_message function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.services.openai.assistant_wrapper import OpenAIAssistantWrapper


class TestStreamMessage:
    """Test OpenAIAssistantWrapper.stream_message function."""

    @pytest.mark.asyncio
    async def test_stream_message_basic(self):
        """Test basic message streaming."""
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_entity_service = AsyncMock()
        
        wrapper = OpenAIAssistantWrapper(mock_agent, mock_entity_service)
        
        # Mock the Runner.run_streamed
        mock_result = AsyncMock()
        mock_result.final_output = "Final response"
        
        # Create mock event
        mock_event = MagicMock()
        mock_event.type = "raw_response_event"
        mock_event.data = MagicMock()
        mock_event.data.delta = "test response"
        
        async def mock_stream_events():
            yield mock_event
        
        mock_result.stream_events = mock_stream_events
        
        with patch("application.services.openai.assistant_wrapper.Runner.run_streamed", return_value=mock_result):
            with patch.object(wrapper, '_extract_hooks_from_result', return_value=[]):
                chunks = []
                async for chunk in wrapper.stream_message(
                    user_message="Hello",
                    conversation_history=[],
                    conversation_id="conv-123"
                ):
                    chunks.append(chunk)
                
                assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_stream_message_with_hooks(self):
        """Test message streaming with hooks."""
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_entity_service = AsyncMock()

        # Mock get_by_id for persistence
        get_response = MagicMock()
        get_response.data = {
            "technical_id": "conv-123",
            "conversation_history": []
        }
        mock_entity_service.get_by_id = AsyncMock(return_value=get_response)
        mock_entity_service.update = AsyncMock()

        wrapper = OpenAIAssistantWrapper(mock_agent, mock_entity_service)

        # Mock the stream_message function to yield hook JSON
        async def mock_stream_gen():
            yield '{"__hook__": {"type": "test_hook", "data": "test"}}'

        with patch("application.services.openai.assistant_wrapper.wrapper.stream_message") as mock_stream:
            mock_stream.return_value = (mock_stream_gen(), "")

            chunks = []
            async for chunk in wrapper.stream_message(
                user_message="Hello",
                conversation_history=[],
                conversation_id="conv-123"
            ):
                chunks.append(chunk)

            # Should have hook JSON in chunks
            assert any("__hook__" in str(chunk) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_stream_message_raw_response_event(self):
        """Test streaming raw response events."""
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_entity_service = AsyncMock()
        
        wrapper = OpenAIAssistantWrapper(mock_agent, mock_entity_service)
        
        mock_result = AsyncMock()
        mock_result.final_output = None
        
        mock_event = MagicMock()
        mock_event.type = "raw_response_event"
        mock_event.data = MagicMock()
        mock_event.data.delta = "streaming text"
        
        async def mock_stream_events():
            yield mock_event
        
        mock_result.stream_events = mock_stream_events
        
        with patch("application.services.openai.assistant_wrapper.Runner.run_streamed", return_value=mock_result):
            with patch.object(wrapper, '_extract_hooks_from_result', return_value=[]):
                chunks = []
                async for chunk in wrapper.stream_message(
                    user_message="Hello",
                    conversation_history=[],
                    conversation_id="conv-123"
                ):
                    chunks.append(chunk)
                
                assert "streaming text" in chunks

    @pytest.mark.asyncio
    async def test_stream_message_run_item_event(self):
        """Test streaming run item events."""
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_entity_service = AsyncMock()
        
        wrapper = OpenAIAssistantWrapper(mock_agent, mock_entity_service)
        
        mock_result = AsyncMock()
        mock_result.final_output = None
        
        # Mock message output item
        mock_content_block = MagicMock()
        mock_content_block.text = "message output"
        
        mock_item = MagicMock()
        mock_item.type = "message_output_item"
        mock_item.content = [mock_content_block]
        
        mock_event = MagicMock()
        mock_event.type = "run_item_stream_event"
        mock_event.item = mock_item
        
        async def mock_stream_events():
            yield mock_event
        
        mock_result.stream_events = mock_stream_events
        
        with patch("application.services.openai.assistant_wrapper.Runner.run_streamed", return_value=mock_result):
            with patch.object(wrapper, '_extract_hooks_from_result', return_value=[]):
                chunks = []
                async for chunk in wrapper.stream_message(
                    user_message="Hello",
                    conversation_history=[],
                    conversation_id="conv-123"
                ):
                    chunks.append(chunk)
                
                assert "message output" in chunks

    @pytest.mark.asyncio
    async def test_stream_message_exception_handling(self):
        """Test stream_message handles exceptions gracefully."""
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_entity_service = AsyncMock()
        
        wrapper = OpenAIAssistantWrapper(mock_agent, mock_entity_service)
        
        with patch("application.services.openai.assistant_wrapper.Runner.run_streamed", side_effect=Exception("Stream error")):
            with pytest.raises(Exception):
                async for chunk in wrapper.stream_message(
                    user_message="Hello",
                    conversation_history=[],
                    conversation_id="conv-123"
                ):
                    pass

