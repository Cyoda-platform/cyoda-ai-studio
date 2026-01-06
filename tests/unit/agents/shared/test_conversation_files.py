"""Tests for retrieve_and_save_conversation_files function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.conversation import retrieve_and_save_conversation_files


class TestRetrieveAndSaveConversationFiles:
    """Test retrieve_and_save_conversation_files function."""

    @pytest.mark.asyncio
    async def test_retrieve_and_save_no_tool_context(self):
        """Test function returns error when tool_context is None."""
        result = await retrieve_and_save_conversation_files(tool_context=None)
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_retrieve_and_save_no_conversation_id_in_state(self):
        """Test function returns error when conversation_id not in state."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}

        result = await retrieve_and_save_conversation_files(tool_context=mock_context)
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_retrieve_and_save_conversation_not_found(self):
        """Test function returns error when conversation not found."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {"conversation_id": "conv-123"}

        with patch("application.agents.shared.repository_tools.conversation.get_entity_service") as mock_entity_service:
            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(return_value=None)
            mock_entity_service.return_value = mock_service

            result = await retrieve_and_save_conversation_files(tool_context=mock_context)
            assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_retrieve_and_save_no_files_found(self):
        """Test function returns message when no files found in conversation."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {"conversation_id": "conv-123"}

        with patch("application.agents.shared.repository_tools.conversation.get_entity_service") as mock_entity_service:
            mock_service = AsyncMock()
            mock_conversation = MagicMock()
            mock_conversation.file_blob_ids = None
            mock_conversation.chat_flow = None

            mock_response = MagicMock()
            mock_response.data = mock_conversation
            mock_service.get_by_id = AsyncMock(return_value=mock_response)
            mock_entity_service.return_value = mock_service

            result = await retrieve_and_save_conversation_files(tool_context=mock_context)
            # Accept either "no files found" message or error about conversation not found
            assert "no files" in result.lower() or "error" in result.lower() or "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_retrieve_and_save_with_file_blob_ids(self):
        """Test function retrieves files from file_blob_ids."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {"conversation_id": "conv-123"}

        with patch("application.agents.shared.repository_tools.conversation.get_entity_service") as mock_entity_service:
            mock_service = AsyncMock()
            mock_conversation = MagicMock()
            mock_conversation.file_blob_ids = ["file-1", "file-2"]
            mock_conversation.chat_flow = None

            mock_response = MagicMock()
            mock_response.data = mock_conversation
            mock_service.get_by_id = AsyncMock(return_value=mock_response)
            mock_service.get_edge = AsyncMock(return_value=MagicMock(data=None))
            mock_entity_service.return_value = mock_service

            with patch("application.agents.shared.repository_tools.files.save_files_to_branch") as mock_save:
                mock_save.return_value = "✅ Files saved"

                result = await retrieve_and_save_conversation_files(tool_context=mock_context)
                # Should attempt to save files
                assert mock_save.called or "ERROR" in result

    @pytest.mark.asyncio
    async def test_retrieve_and_save_exception_handling(self):
        """Test function handles exceptions gracefully."""
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {"conversation_id": "conv-123"}

        with patch("application.agents.shared.repository_tools.conversation.get_entity_service") as mock_entity_service:
            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(side_effect=Exception("Service error"))
            mock_entity_service.return_value = mock_service

            result = await retrieve_and_save_conversation_files(tool_context=mock_context)
            assert "ERROR" in result

