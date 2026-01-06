"""Unit tests for get_user_info tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_tool_context():
    """Create a mock tool context."""
    context = MagicMock()
    context.state = {
        "conversation_id": "conv-123",
        "user_id": "test.user",
        "repository_name": "test-repo",
        "branch_name": "main",
        "language": "python",
    }
    return context


class TestGetUserInfo:
    """Test get_user_info tool functionality."""

    @pytest.mark.asyncio
    async def test_get_user_info_imports_successfully(self):
        """Test get_user_info can be imported."""
        try:
            from application.agents.setup.tools import get_user_info
            assert callable(get_user_info)
        except ImportError as e:
            pytest.fail(f"Failed to import get_user_info: {e}")

    @pytest.mark.asyncio
    async def test_get_user_info_with_guest_user(self, mock_tool_context):
        """Test get_user_info with guest user."""
        from application.agents.setup.tools import get_user_info

        mock_tool_context.state["user_id"] = "guest.user123"

        with patch('services.services.get_entity_service') as mock_entity_service:
            mock_service = AsyncMock()
            mock_entity_service.return_value = mock_service

            # Mock conversation response
            mock_conversation = MagicMock()
            mock_conversation.data = {"workflowCache": {}}
            mock_service.get_by_id = AsyncMock(return_value=mock_conversation)

            result = await get_user_info("test request", mock_tool_context)

            assert isinstance(result, str)
            assert "guest" in result.lower() or "log in" in result.lower()

    @pytest.mark.asyncio
    async def test_get_user_info_with_authenticated_user(self, mock_tool_context):
        """Test get_user_info with authenticated user."""
        from application.agents.setup.tools import get_user_info

        mock_tool_context.state["user_id"] = "authenticated.user"

        # Mock conversation entity with workflowCache
        mock_conversation = MagicMock()
        mock_conversation.data = {
            "workflowCache": {
                "repository_name": "test-repo",
                "repository_branch": "main",
                "language": "python",
            }
        }

        with patch('services.services.get_entity_service') as mock_entity_service:
            mock_service = AsyncMock()
            mock_entity_service.return_value = mock_service
            mock_service.get_by_id = AsyncMock(return_value=mock_conversation)

            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                mock_client_instance.get = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 401  # Environment exists
                mock_client_instance.get.return_value = mock_response

                result = await get_user_info("test request", mock_tool_context)

                assert isinstance(result, str)
                assert "test-repo" in result or "repository" in result.lower()

    @pytest.mark.asyncio
    async def test_get_user_info_includes_repository_info(self, mock_tool_context):
        """Test get_user_info includes repository information."""
        from application.agents.setup.tools import get_user_info

        # Mock conversation with repository info
        mock_conversation = MagicMock()
        mock_conversation.data = {
            "workflowCache": {
                "repository_name": "test-repo",
                "branch_name": "main"
            }
        }

        with patch('services.services.get_entity_service') as mock_entity_service:
            mock_service = AsyncMock()
            mock_entity_service.return_value = mock_service
            mock_service.get_by_id = AsyncMock(return_value=mock_conversation)

            result = await get_user_info("test request", mock_tool_context)

            assert isinstance(result, str)
            # Should contain key information from state
            assert len(result) > 0
            assert "test-repo" in result

    @pytest.mark.asyncio
    async def test_get_user_info_handles_missing_conversation(self, mock_tool_context):
        """Test get_user_info handles missing conversation gracefully."""
        from application.agents.setup.tools import get_user_info

        mock_tool_context.state["conversation_id"] = None

        # Even without conversation_id, should return basic user info
        result = await get_user_info("test request", mock_tool_context)

        # Should still return a string result
        assert isinstance(result, str)
        # Should include basic info like user_id
        assert "test.user" in result or "user_id" in result

    @pytest.mark.asyncio
    async def test_get_user_info_handles_errors_gracefully(self, mock_tool_context):
        """Test get_user_info handles errors gracefully."""
        from application.agents.setup.tools import get_user_info

        with patch('services.services.get_entity_service', side_effect=Exception("Service error")):
            result = await get_user_info("test request", mock_tool_context)

            # Should still return a string with basic user info even if entity service fails
            assert isinstance(result, str)
            # Should contain basic user information despite error
            assert "user_logged_in_most_recent_status" in result or "test.user" in result


class TestSetupToolsOtherFunctions:
    """Test other functions in setup tools."""

    @pytest.mark.asyncio
    async def test_validate_environment_imports(self):
        """Test validate_environment can be imported."""
        try:
            from application.agents.setup.tools import validate_environment
            assert callable(validate_environment)
        except ImportError as e:
            pytest.fail(f"Failed to import validate_environment: {e}")

    @pytest.mark.asyncio
    async def test_check_project_structure_imports(self):
        """Test check_project_structure can be imported."""
        try:
            from application.agents.setup.tools import check_project_structure
            assert callable(check_project_structure)
        except ImportError as e:
            pytest.fail(f"Failed to import check_project_structure: {e}")
