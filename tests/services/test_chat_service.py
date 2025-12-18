"""
Unit tests for ChatService.

Tests business logic without HTTP dependencies.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from application.entity.conversation import Conversation
from application.services.chat_service import ChatService
from tests.fixtures.conversation_fixtures import (
    create_test_conversation,
    create_test_conversation_with_messages,
    create_conversation_list_response,
)


class TestChatServiceCreate:
    """Test conversation creation."""

    @pytest.mark.asyncio
    async def test_create_conversation_success(self):
        """Test successful conversation creation."""
        # Arrange
        mock_repo = Mock()
        mock_repo.create = AsyncMock(
            return_value=create_test_conversation(
                technical_id="created-123",
                user_id="alice",
                name="New Chat"
            )
        )
        mock_persistence = Mock()

        service = ChatService(mock_repo, mock_persistence)

        # Act
        result = await service.create_conversation(
            user_id="alice",
            name="New Chat",
            description="Test description"
        )

        # Assert
        assert result.technical_id == "created-123"
        assert result.user_id == "alice"
        assert result.name == "New Chat"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_conversation_invalidates_cache(self):
        """Test that creating conversation invalidates cache."""
        # Arrange
        mock_repo = Mock()
        mock_repo.create = AsyncMock(
            return_value=create_test_conversation(user_id="alice")
        )
        mock_persistence = Mock()

        service = ChatService(mock_repo, mock_persistence)

        # Pre-populate cache
        service._chat_list_cache["chats:alice"] = ([], datetime.now(timezone.utc).timestamp())

        # Act
        await service.create_conversation(user_id="alice", name="New")

        # Assert - cache should be invalidated
        assert "chats:alice" not in service._chat_list_cache


class TestChatServiceUpdate:
    """Test conversation updates."""

    @pytest.mark.asyncio
    async def test_update_conversation_success(self):
        """Test successful conversation update."""
        # Arrange
        conversation = create_test_conversation(name="Old Name")
        conversation.name = "New Name"

        mock_repo = Mock()
        mock_repo.update_with_retry = AsyncMock(return_value=conversation)
        mock_persistence = Mock()

        service = ChatService(mock_repo, mock_persistence)

        # Act
        result = await service.update_conversation(conversation)

        # Assert
        assert result.name == "New Name"
        mock_repo.update_with_retry.assert_called_once_with(conversation)

    @pytest.mark.asyncio
    async def test_update_conversation_invalidates_cache(self):
        """Test that updating conversation invalidates cache."""
        # Arrange
        conversation = create_test_conversation(user_id="alice")

        mock_repo = Mock()
        mock_repo.update_with_retry = AsyncMock(return_value=conversation)
        mock_persistence = Mock()

        service = ChatService(mock_repo, mock_persistence)

        # Pre-populate cache
        service._chat_list_cache["chats:alice"] = ([], datetime.now(timezone.utc).timestamp())

        # Act
        await service.update_conversation(conversation)

        # Assert
        assert "chats:alice" not in service._chat_list_cache


class TestChatServiceValidation:
    """Test ownership validation."""

    def test_validate_ownership_success_owner(self):
        """Test validation succeeds for owner."""
        # Arrange
        conversation = create_test_conversation(user_id="alice")
        service = ChatService(Mock(), Mock())

        # Act & Assert - should not raise
        service.validate_ownership(conversation, "alice", is_superuser=False)

    def test_validate_ownership_success_superuser(self):
        """Test validation succeeds for superuser."""
        # Arrange
        conversation = create_test_conversation(user_id="alice")
        service = ChatService(Mock(), Mock())

        # Act & Assert - should not raise
        service.validate_ownership(conversation, "bob", is_superuser=True)

    def test_validate_ownership_fails_not_owner(self):
        """Test validation fails for non-owner."""
        # Arrange
        conversation = create_test_conversation(user_id="alice")
        service = ChatService(Mock(), Mock())

        # Act & Assert
        with pytest.raises(PermissionError, match="does not have access"):
            service.validate_ownership(conversation, "bob", is_superuser=False)


class TestChatServiceTransfer:
    """Test guest chat transfer."""

    @pytest.mark.asyncio
    async def test_transfer_guest_chats_success(self):
        """Test successful chat transfer from guest to user."""
        # Arrange
        guest_chats = create_conversation_list_response(
            count=3,
            user_id="guest.123"
        )

        mock_repo = Mock()
        mock_repo.search = AsyncMock(return_value=guest_chats)
        mock_repo.get_by_id = AsyncMock(
            side_effect=[
                create_test_conversation(technical_id=f"conv-{i}", user_id="guest.123")
                for i in range(3)
            ]
        )
        mock_repo.update_with_retry = AsyncMock(
            side_effect=lambda conv: conv
        )
        mock_persistence = Mock()

        service = ChatService(mock_repo, mock_persistence)

        # Act
        count = await service.transfer_guest_chats("guest.123", "alice")

        # Assert
        assert count == 3
        assert mock_repo.update_with_retry.call_count == 3

    @pytest.mark.asyncio
    async def test_transfer_guest_chats_validates_source(self):
        """Test transfer rejects non-guest source."""
        # Arrange
        service = ChatService(Mock(), Mock())

        # Act & Assert
        with pytest.raises(ValueError, match="must be a guest user"):
            await service.transfer_guest_chats("alice", "bob")

    @pytest.mark.asyncio
    async def test_transfer_guest_chats_validates_target(self):
        """Test transfer rejects guest target."""
        # Arrange
        service = ChatService(Mock(), Mock())

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot transfer chats to guest"):
            await service.transfer_guest_chats("guest.123", "guest.456")


class TestChatServiceCaching:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_list_conversations_uses_cache(self):
        """Test that list uses cache when available."""
        # Arrange
        cached_chats = [
            {"technical_id": "conv-1", "name": "Chat 1", "date": "2025-01-01"}
        ]

        mock_repo = Mock()
        mock_persistence = Mock()

        service = ChatService(mock_repo, mock_persistence)

        # Pre-populate cache with recent timestamp
        cache_key = "chats:alice"
        service._chat_list_cache[cache_key] = (
            cached_chats,
            datetime.now(timezone.utc).timestamp()
        )

        # Act
        result = await service.list_conversations(user_id="alice", use_cache=True)

        # Assert
        assert result["cached"] is True
        assert result["chats"] == cached_chats
        mock_repo.search.assert_not_called()  # Should not hit database

    @pytest.mark.asyncio
    async def test_list_conversations_bypasses_cache_when_disabled(self):
        """Test that cache can be bypassed."""
        # Arrange
        mock_repo = Mock()
        mock_repo.search = AsyncMock(return_value=[])
        mock_persistence = Mock()

        service = ChatService(mock_repo, mock_persistence)

        # Pre-populate cache
        service._chat_list_cache["chats:alice"] = (
            [{"technical_id": "cached"}],
            datetime.now(timezone.utc).timestamp()
        )

        # Act
        result = await service.list_conversations(
            user_id="alice",
            use_cache=False
        )

        # Assert
        assert result["cached"] is False
        mock_repo.search.assert_called_once()  # Should hit database

    def test_invalidate_cache(self):
        """Test cache invalidation."""
        # Arrange
        service = ChatService(Mock(), Mock())
        service._chat_list_cache["chats:alice"] = ([], 0)
        service._chat_list_cache["chats:bob"] = ([], 0)

        # Act
        service.invalidate_cache("alice")

        # Assert
        assert "chats:alice" not in service._chat_list_cache
        assert "chats:bob" in service._chat_list_cache  # Other users unaffected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
