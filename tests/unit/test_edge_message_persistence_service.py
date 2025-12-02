"""
Tests for Edge Message Persistence Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from application.services.edge_message_persistence_service import (
    EdgeMessagePersistenceService,
)


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return AsyncMock()


@pytest.fixture
def persistence_service(mock_repository):
    """Create a persistence service with mock repository."""
    return EdgeMessagePersistenceService(repository=mock_repository)


class TestEdgeMessagePersistenceService:
    """Test suite for edge message persistence service."""

    @pytest.mark.asyncio
    async def test_save_message_as_edge_message_success(self, persistence_service, mock_repository):
        """Test saving a message as an edge message successfully."""
        mock_repository.save.return_value = "edge-msg-123"

        result = await persistence_service.save_message_as_edge_message(
            message_type="answer",
            message_content="Hello, world!",
            conversation_id="conv-123",
            user_id="user-123",
        )

        assert result == "edge-msg-123"
        mock_repository.save.assert_called_once()

        # Verify the call arguments
        call_args = mock_repository.save.call_args
        assert call_args[1]["meta"]["type"] == "EDGE_MESSAGE"
        assert call_args[1]["meta"]["entity_model"] == "flow_edge_message"
        assert call_args[1]["entity"]["type"] == "answer"
        assert call_args[1]["entity"]["message"] == "Hello, world!"
        assert call_args[1]["entity"]["conversation_id"] == "conv-123"
        assert call_args[1]["entity"]["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_save_message_with_metadata(self, persistence_service, mock_repository):
        """Test saving a message with metadata."""
        mock_repository.save.return_value = "edge-msg-456"
        metadata = {"hook": {"type": "confirmation"}}

        result = await persistence_service.save_message_as_edge_message(
            message_type="question",
            message_content="Response text",
            conversation_id="conv-123",
            user_id="user-123",
            metadata=metadata,
        )

        assert result == "edge-msg-456"
        call_args = mock_repository.save.call_args
        assert call_args[1]["entity"]["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_save_message_with_file_blob_ids(self, persistence_service, mock_repository):
        """Test saving a message with file attachments."""
        mock_repository.save.return_value = "edge-msg-789"
        file_ids = ["file-1", "file-2"]

        result = await persistence_service.save_message_as_edge_message(
            message_type="answer",
            message_content="Message with files",
            conversation_id="conv-123",
            user_id="user-123",
            file_blob_ids=file_ids,
        )

        assert result == "edge-msg-789"
        call_args = mock_repository.save.call_args
        assert call_args[1]["entity"]["file_blob_ids"] == file_ids

    @pytest.mark.asyncio
    async def test_save_message_failure(self, persistence_service, mock_repository):
        """Test handling of save failure."""
        mock_repository.save.return_value = None

        result = await persistence_service.save_message_as_edge_message(
            message_type="answer",
            message_content="Test",
            conversation_id="conv-123",
            user_id="user-123",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_save_streaming_debug_history(self, persistence_service, mock_repository):
        """Test saving streaming debug history."""
        mock_repository.save.return_value = "debug-msg-123"
        streaming_events = [
            {"type": "start", "timestamp": "2025-11-21T12:00:00Z"},
            {"type": "content", "timestamp": "2025-11-21T12:00:01Z", "chunk_length": 50},
            {"type": "done", "timestamp": "2025-11-21T12:00:02Z"},
        ]

        result = await persistence_service.save_streaming_debug_history(
            conversation_id="conv-123",
            user_id="user-123",
            streaming_events=streaming_events,
        )

        assert result == "debug-msg-123"
        call_args = mock_repository.save.call_args
        assert call_args[1]["entity"]["type"] == "streaming_debug_history"
        assert call_args[1]["entity"]["events_count"] == 3
        assert call_args[1]["entity"]["events"] == streaming_events

    @pytest.mark.asyncio
    async def test_save_response_with_history(self, persistence_service, mock_repository):
        """Test saving response with streaming debug history in single edge message."""
        mock_repository.save.return_value = "response-msg-123"
        streaming_events = [
            {"type": "start", "timestamp": "2025-11-21T12:00:00Z"},
            {"type": "content", "timestamp": "2025-11-21T12:00:01Z", "chunk_length": 100},
        ]

        result = await persistence_service.save_response_with_history(
            conversation_id="conv-123",
            user_id="user-123",
            response_content="AI response",
            streaming_events=streaming_events,
        )

        assert result == "response-msg-123"
        mock_repository.save.assert_called_once()

        # Verify debug history is included in the edge message
        call_args = mock_repository.save.call_args
        assert call_args[1]["entity"]["debug_history"]["type"] == "streaming_debug_history"
        assert call_args[1]["entity"]["debug_history"]["events_count"] == 2

    @pytest.mark.asyncio
    async def test_save_response_with_history_and_metadata(self, persistence_service, mock_repository):
        """Test saving response with metadata."""
        mock_repository.save.return_value = "response-msg-123"
        metadata = {"hook": {"type": "confirmation"}}
        streaming_events = [{"type": "done", "timestamp": "2025-11-21T12:00:00Z"}]

        result = await persistence_service.save_response_with_history(
            conversation_id="conv-123",
            user_id="user-123",
            response_content="Response",
            streaming_events=streaming_events,
            metadata=metadata,
        )

        assert result == "response-msg-123"
        # Verify metadata was included in the edge message
        call_args = mock_repository.save.call_args
        assert call_args[1]["entity"]["metadata"] == metadata
        assert call_args[1]["entity"]["debug_history"]["events_count"] == 1

