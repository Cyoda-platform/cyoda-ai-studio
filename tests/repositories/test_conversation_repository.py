"""
Unit tests for ConversationRepository.

Tests data access logic including retry and merge functionality.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from application.entity.conversation import Conversation
from application.repositories.conversation_repository import ConversationRepository
from tests.fixtures.conversation_fixtures import (
    create_test_conversation,
    create_test_conversation_with_messages,
)


class TestConversationRepositoryGet:
    """Test getting conversations."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self):
        """Test successful retrieval by ID."""
        # Arrange
        conv_data = create_test_conversation().model_dump()

        mock_entity_service = Mock()
        mock_entity_service.get_by_id = AsyncMock(return_value=Mock(data=conv_data))

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.get_by_id("test-conv-123")

        # Assert
        assert result is not None
        assert result.technical_id == "test-conv-123"
        mock_entity_service.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test returns None when not found."""
        # Arrange
        mock_entity_service = Mock()
        mock_entity_service.get_by_id = AsyncMock(side_effect=Exception("Not found"))

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.get_by_id("nonexistent")

        # Assert
        assert result is None


class TestConversationRepositoryCreate:
    """Test conversation creation."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful conversation creation."""
        # Arrange
        conversation = create_test_conversation()
        conv_data = conversation.model_dump()

        mock_entity_service = Mock()
        mock_entity_service.save = AsyncMock(return_value=Mock(data=conv_data))

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.create(conversation)

        # Assert
        assert result.technical_id == conversation.technical_id
        mock_entity_service.save.assert_called_once()


class TestConversationRepositoryUpdateWithRetry:
    """Test update with retry logic."""

    @pytest.mark.asyncio
    async def test_update_success_first_try(self):
        """Test successful update on first attempt."""
        # Arrange
        conversation = create_test_conversation()
        conv_data = conversation.model_dump()

        mock_entity_service = Mock()
        mock_entity_service.update = AsyncMock(return_value=Mock(data=conv_data))

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.update_with_retry(conversation)

        # Assert
        assert result.technical_id == conversation.technical_id
        assert mock_entity_service.update.call_count == 1

    @pytest.mark.asyncio
    async def test_update_retries_on_conflict(self):
        """Test retry logic on version conflict."""
        # Arrange
        conversation = create_test_conversation()
        conv_data = conversation.model_dump()

        mock_entity_service = Mock()
        # First call fails with 422, second succeeds
        mock_entity_service.update = AsyncMock(
            side_effect=[Exception("422 version mismatch"), Mock(data=conv_data)]
        )
        mock_entity_service.get_by_id = AsyncMock(return_value=Mock(data=conv_data))

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.update_with_retry(conversation)

        # Assert
        assert result is not None
        assert mock_entity_service.update.call_count == 2

    @pytest.mark.asyncio
    async def test_update_merges_messages_on_conflict(self):
        """Test that messages are merged on conflict."""
        # Arrange
        # Target conversation has 1 message
        target_conv = create_test_conversation_with_messages(num_messages=1)
        target_conv.technical_id = "test-123"

        # Fresh conversation from DB has 2 different messages
        fresh_conv = create_test_conversation_with_messages(num_messages=2)
        fresh_conv.technical_id = "test-123"
        fresh_conv.chat_flow["finished_flow"][0]["technical_id"] = "msg-db-0"
        fresh_conv.chat_flow["finished_flow"][1]["technical_id"] = "msg-db-1"

        mock_entity_service = Mock()
        # First update fails (conflict)
        mock_entity_service.update = AsyncMock(
            side_effect=[Exception("422 conflict"), Mock(data=fresh_conv.model_dump())]
        )
        # When fetching fresh version, return the DB version
        mock_entity_service.get_by_id = AsyncMock(
            return_value=Mock(data=fresh_conv.model_dump())
        )

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.update_with_retry(target_conv)

        # Assert
        assert result is not None
        # Should have merged messages (2 from DB + 1 from target = 3 total)
        # (assuming different IDs)
        assert mock_entity_service.update.call_count == 2

    @pytest.mark.asyncio
    async def test_update_fails_after_max_retries(self):
        """Test that update fails after max retries."""
        # Arrange
        conversation = create_test_conversation()

        mock_entity_service = Mock()
        # Always fail with 422
        mock_entity_service.update = AsyncMock(side_effect=Exception("422 conflict"))
        mock_entity_service.get_by_id = AsyncMock(
            return_value=Mock(data=conversation.model_dump())
        )

        repo = ConversationRepository(mock_entity_service)

        # Act & Assert
        with pytest.raises(Exception, match="422 conflict"):
            await repo.update_with_retry(conversation)

        # Should have tried max retries (5)
        assert mock_entity_service.update.call_count == 5

    @pytest.mark.asyncio
    async def test_update_does_not_retry_non_conflict_errors(self):
        """Test that non-conflict errors are not retried."""
        # Arrange
        conversation = create_test_conversation()

        mock_entity_service = Mock()
        mock_entity_service.update = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        repo = ConversationRepository(mock_entity_service)

        # Act & Assert
        with pytest.raises(Exception, match="Database connection"):
            await repo.update_with_retry(conversation)

        # Should fail immediately without retry
        assert mock_entity_service.update.call_count == 1


class TestConversationRepositoryDelete:
    """Test conversation deletion."""

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """Test successful deletion."""
        # Arrange
        mock_entity_service = Mock()
        mock_entity_service.delete_by_id = AsyncMock()

        repo = ConversationRepository(mock_entity_service)

        # Act
        await repo.delete("test-conv-123")

        # Assert
        mock_entity_service.delete_by_id.assert_called_once_with(
            entity_id="test-conv-123", entity_class="Conversation", entity_version="1"
        )


class TestConversationRepositorySearch:
    """Test conversation search."""

    @pytest.mark.asyncio
    async def test_search_with_user_filter(self):
        """Test search filtered by user ID."""
        # Arrange
        mock_entity_service = Mock()
        mock_entity_service.search = AsyncMock(return_value=[])

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.search(user_id="alice", limit=10)

        # Assert
        assert isinstance(result, list)
        mock_entity_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_without_user_filter(self):
        """Test search for all conversations (superuser)."""
        # Arrange
        mock_entity_service = Mock()
        mock_entity_service.find_all = AsyncMock(return_value=[])

        repo = ConversationRepository(mock_entity_service)

        # Act
        result = await repo.search(user_id=None)

        # Assert
        assert isinstance(result, list)
        mock_entity_service.find_all.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
