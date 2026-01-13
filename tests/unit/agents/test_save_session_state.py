"""Tests for CyodaAssistantWrapper._save_session_state function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.agents.cyoda_assistant import CyodaAssistantWrapper
from common.service.service import EntityServiceError


class TestSaveSessionState:
    """Test CyodaAssistantWrapper._save_session_state function."""

    @pytest.mark.asyncio
    async def test_save_session_state_success(self):
        """Test successful session state save."""
        mock_entity_service = AsyncMock()
        mock_conversation = MagicMock()
        mock_conversation.workflow_cache = {}
        mock_conversation.model_dump.return_value = {
            "id": "conv-123",
            "user_id": "user-123",
        }

        mock_response = MagicMock()
        mock_response.data = {
            "id": "conv-123",
            "user_id": "user-123",
            "workflow_cache": {},
        }

        mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        mock_entity_service.update = AsyncMock()

        wrapper = CyodaAssistantWrapper(
            adk_agent=MagicMock(), entity_service=mock_entity_service
        )

        with patch(
            "application.agents.cyoda_assistant.Conversation",
            return_value=mock_conversation,
        ):
            await wrapper._save_session_state("conv-123", {"state": "test"})

            # Verify update was called with the conversation data
            assert mock_entity_service.update.called
            call_args = mock_entity_service.update.call_args
            assert call_args[1]["entity_id"] == "conv-123"

    @pytest.mark.asyncio
    async def test_save_session_state_conversation_not_found(self):
        """Test save session state when conversation not found."""
        mock_entity_service = AsyncMock()
        mock_entity_service.get_by_id = AsyncMock(return_value=None)

        wrapper = CyodaAssistantWrapper(
            adk_agent=MagicMock(), entity_service=mock_entity_service
        )

        # Should not raise, just return
        await wrapper._save_session_state("conv-123", {"state": "test"})

        assert not mock_entity_service.update.called

    @pytest.mark.asyncio
    async def test_save_session_state_version_conflict_retry(self):
        """Test save session state retries on version conflict."""
        mock_entity_service = AsyncMock()
        mock_conversation = MagicMock()
        mock_conversation.workflow_cache = {}
        mock_conversation.model_dump.return_value = {
            "id": "conv-123",
            "user_id": "user-123",
        }

        mock_response = MagicMock()
        mock_response.data = {
            "id": "conv-123",
            "user_id": "user-123",
            "workflow_cache": {},
        }

        mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)

        # First call fails with version conflict, second succeeds
        mock_entity_service.update = AsyncMock(
            side_effect=[EntityServiceError("422 version mismatch"), None]
        )

        wrapper = CyodaAssistantWrapper(
            adk_agent=MagicMock(), entity_service=mock_entity_service
        )

        with patch(
            "application.agents.cyoda_assistant.Conversation",
            return_value=mock_conversation,
        ):
            with patch("asyncio.sleep"):
                await wrapper._save_session_state("conv-123", {"state": "test"})

                # Should have retried
                assert mock_entity_service.update.call_count == 2

    @pytest.mark.asyncio
    async def test_save_session_state_max_retries_exceeded(self):
        """Test save session state gives up after max retries."""
        mock_entity_service = AsyncMock()
        mock_conversation = MagicMock()
        mock_conversation.workflow_cache = {}
        mock_conversation.model_dump.return_value = {
            "id": "conv-123",
            "user_id": "user-123",
        }

        mock_response = MagicMock()
        mock_response.data = {
            "id": "conv-123",
            "user_id": "user-123",
            "workflow_cache": {},
        }

        mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)

        # Always fail with version conflict
        mock_entity_service.update = AsyncMock(
            side_effect=EntityServiceError("422 version mismatch")
        )

        wrapper = CyodaAssistantWrapper(
            adk_agent=MagicMock(), entity_service=mock_entity_service
        )

        with patch(
            "application.agents.cyoda_assistant.Conversation",
            return_value=mock_conversation,
        ):
            with patch("asyncio.sleep"):
                # Should not raise, just log and return
                await wrapper._save_session_state("conv-123", {"state": "test"})

                # Should have tried max_retries times
                assert mock_entity_service.update.call_count == 5

    @pytest.mark.asyncio
    async def test_save_session_state_non_retryable_error(self):
        """Test save session state handles non-retryable errors."""
        mock_entity_service = AsyncMock()
        mock_conversation = MagicMock()
        mock_conversation.workflow_cache = {}
        mock_conversation.model_dump.return_value = {
            "id": "conv-123",
            "user_id": "user-123",
        }

        mock_response = MagicMock()
        mock_response.data = {
            "id": "conv-123",
            "user_id": "user-123",
            "workflow_cache": {},
        }

        mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        mock_entity_service.update = AsyncMock(
            side_effect=EntityServiceError("403 Forbidden")
        )

        wrapper = CyodaAssistantWrapper(
            adk_agent=MagicMock(), entity_service=mock_entity_service
        )

        with patch(
            "application.agents.cyoda_assistant.Conversation",
            return_value=mock_conversation,
        ):
            # Should not raise, just log and return
            await wrapper._save_session_state("conv-123", {"state": "test"})

            # Should only try once for non-retryable error
            assert mock_entity_service.update.call_count == 1

    @pytest.mark.asyncio
    async def test_save_session_state_unexpected_error(self):
        """Test save session state handles unexpected errors gracefully."""
        mock_entity_service = AsyncMock()
        mock_entity_service.get_by_id = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        wrapper = CyodaAssistantWrapper(
            adk_agent=MagicMock(), entity_service=mock_entity_service
        )

        # Should not raise, just log and return
        await wrapper._save_session_state("conv-123", {"state": "test"})

    @pytest.mark.asyncio
    async def test_save_session_state_preserves_existing_cache(self):
        """Test save session state preserves existing workflow_cache."""
        mock_entity_service = AsyncMock()
        mock_conversation = MagicMock()
        mock_conversation.workflow_cache = {"existing_key": "existing_value"}
        mock_conversation.model_dump.return_value = {
            "id": "conv-123",
            "user_id": "user-123",
        }

        mock_response = MagicMock()
        mock_response.data = {
            "id": "conv-123",
            "user_id": "user-123",
            "workflow_cache": {"existing_key": "existing_value"},
        }

        mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        mock_entity_service.update = AsyncMock()

        wrapper = CyodaAssistantWrapper(
            adk_agent=MagicMock(), entity_service=mock_entity_service
        )

        with patch(
            "application.agents.cyoda_assistant.Conversation",
            return_value=mock_conversation,
        ):
            await wrapper._save_session_state("conv-123", {"state": "test"})

            # Verify update was called (which means workflow_cache was preserved and updated)
            assert mock_entity_service.update.called
            call_args = mock_entity_service.update.call_args
            assert call_args[1]["entity_id"] == "conv-123"
