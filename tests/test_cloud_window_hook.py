"""
Tests for cloud_window hook functionality.

Verifies that environment tools correctly create and store cloud_window hooks
for UI integration.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from google.adk.tools.tool_context import ToolContext

from application.agents.environment.tools import check_environment_exists
from application.agents.shared.hook_utils import create_cloud_window_hook


class TestCloudWindowHookCreation:
    """Test suite for cloud_window hook creation utility."""

    def test_create_cloud_window_hook_minimal(self):
        """Test creating cloud_window hook with minimal parameters."""
        hook = create_cloud_window_hook(
            conversation_id="test-conv-123"
        )

        assert hook["type"] == "cloud_window"
        assert hook["action"] == "open_environments_panel"
        assert hook["data"]["conversation_id"] == "test-conv-123"
        assert "message" in hook["data"]
        assert hook["data"]["message"] == "View your Cyoda environment details in the Cloud panel."

    def test_create_cloud_window_hook_with_environment_url(self):
        """Test creating cloud_window hook with environment URL."""
        hook = create_cloud_window_hook(
            conversation_id="test-conv-123",
            environment_url="https://client-testuser.cyoda.cloud"
        )

        assert hook["data"]["environment_url"] == "https://client-testuser.cyoda.cloud"

    def test_create_cloud_window_hook_with_status(self):
        """Test creating cloud_window hook with environment status."""
        hook = create_cloud_window_hook(
            conversation_id="test-conv-123",
            environment_status="deployed"
        )

        assert hook["data"]["environment_status"] == "deployed"

    def test_create_cloud_window_hook_with_custom_message(self):
        """Test creating cloud_window hook with custom message."""
        custom_message = "Your environment is ready! Check it out."
        hook = create_cloud_window_hook(
            conversation_id="test-conv-123",
            message=custom_message
        )

        assert hook["data"]["message"] == custom_message

    def test_create_cloud_window_hook_all_parameters(self):
        """Test creating cloud_window hook with all parameters."""
        hook = create_cloud_window_hook(
            conversation_id="test-conv-123",
            environment_url="https://client-testuser.cyoda.cloud",
            environment_status="deploying",
            message="Deployment in progress!"
        )

        assert hook["type"] == "cloud_window"
        assert hook["action"] == "open_environments_panel"
        assert hook["data"]["conversation_id"] == "test-conv-123"
        assert hook["data"]["environment_url"] == "https://client-testuser.cyoda.cloud"
        assert hook["data"]["environment_status"] == "deploying"
        assert hook["data"]["message"] == "Deployment in progress!"


class TestCheckEnvironmentExistsHook:
    """Test suite for check_environment_exists tool hook integration."""

    @pytest.mark.asyncio
    async def test_check_environment_exists_creates_hook_when_deployed(self):
        """Test that check_environment_exists creates hook when environment is deployed."""
        # Mock tool context
        tool_context = ToolContext(state={
            "user_id": "testuser",
            "conversation_id": "test-conv-123"
        })

        # Mock send_get_request to raise InvalidTokenException (environment exists)
        with patch("application.agents.environment.tools.send_get_request") as mock_request:
            from common.exception.exceptions import InvalidTokenException
            mock_request.side_effect = InvalidTokenException("Invalid token")

            # Call the tool
            result = await check_environment_exists(tool_context)

            # Verify hook was created and stored
            assert "last_tool_hook" in tool_context.state
            hook = tool_context.state["last_tool_hook"]

            # Verify hook structure
            assert hook["type"] == "cloud_window"
            assert hook["action"] == "open_environments_panel"
            assert hook["data"]["conversation_id"] == "test-conv-123"
            assert hook["data"]["environment_status"] == "deployed"
            assert "client-testuser" in hook["data"]["environment_url"]

            # Verify result contains hook
            result_data = json.loads(result)
            assert "hook" in result_data

    @pytest.mark.asyncio
    async def test_check_environment_exists_creates_hook_when_not_deployed(self):
        """Test that check_environment_exists creates hook when environment is not deployed."""
        # Mock tool context
        tool_context = ToolContext(state={
            "user_id": "testuser",
            "conversation_id": "test-conv-123"
        })

        # Mock send_get_request to raise generic exception (environment doesn't exist)
        with patch("application.agents.environment.tools.send_get_request") as mock_request:
            mock_request.side_effect = Exception("Connection refused")

            # Call the tool
            result = await check_environment_exists(tool_context)

            # Verify hook was created and stored
            assert "last_tool_hook" in tool_context.state
            hook = tool_context.state["last_tool_hook"]

            # Verify hook structure
            assert hook["type"] == "cloud_window"
            assert hook["data"]["environment_status"] == "not_deployed"
            assert "client-testuser" in hook["data"]["environment_url"]

    @pytest.mark.asyncio
    async def test_check_environment_exists_no_hook_for_guest(self):
        """Test that check_environment_exists doesn't create hook for guest users."""
        # Mock tool context with guest user
        tool_context = ToolContext(state={
            "user_id": "guest_12345",
            "conversation_id": "test-conv-123"
        })

        # Call the tool
        result = await check_environment_exists(tool_context)

        # Verify no hook was created
        assert "last_tool_hook" not in tool_context.state

        # Verify result indicates guest user
        result_data = json.loads(result)
        assert result_data["exists"] is False
        assert "not logged in" in result_data["message"].lower()

    @pytest.mark.asyncio
    async def test_check_environment_exists_no_hook_without_conversation_id(self):
        """Test that check_environment_exists doesn't create hook without conversation_id."""
        # Mock tool context without conversation_id
        tool_context = ToolContext(state={
            "user_id": "testuser"
            # No conversation_id
        })

        # Mock send_get_request
        with patch("application.agents.environment.tools.send_get_request") as mock_request:
            from common.exception.exceptions import InvalidTokenException
            mock_request.side_effect = InvalidTokenException("Invalid token")

            # Call the tool
            result = await check_environment_exists(tool_context)

            # Verify no hook was created (no conversation_id)
            assert "last_tool_hook" not in tool_context.state

            # But result should still be valid JSON
            result_data = json.loads(result)
            assert result_data["exists"] is True


class TestHookIntegration:
    """Test suite for hook integration with streaming service."""

    def test_hook_serialization(self):
        """Test that hooks can be properly serialized to JSON."""
        hook = create_cloud_window_hook(
            conversation_id="test-conv-123",
            environment_url="https://client-testuser.cyoda.cloud",
            environment_status="deployed",
            message="Environment is ready!"
        )

        # Serialize to JSON
        hook_json = json.dumps(hook)

        # Deserialize back
        hook_deserialized = json.loads(hook_json)

        # Verify structure is preserved
        assert hook_deserialized["type"] == "cloud_window"
        assert hook_deserialized["action"] == "open_environments_panel"
        assert hook_deserialized["data"]["conversation_id"] == "test-conv-123"
        assert hook_deserialized["data"]["environment_url"] == "https://client-testuser.cyoda.cloud"
        assert hook_deserialized["data"]["environment_status"] == "deployed"

    def test_hook_in_tool_context_state(self):
        """Test that hooks are properly stored in tool context state."""
        tool_context = ToolContext(state={
            "user_id": "testuser",
            "conversation_id": "test-conv-123"
        })

        # Create and store hook
        hook = create_cloud_window_hook(
            conversation_id="test-conv-123",
            environment_status="deployed"
        )
        tool_context.state["last_tool_hook"] = hook

        # Verify hook is in state
        assert "last_tool_hook" in tool_context.state
        stored_hook = tool_context.state["last_tool_hook"]
        assert stored_hook["type"] == "cloud_window"
        assert stored_hook["data"]["conversation_id"] == "test-conv-123"

    def test_wrap_response_with_hook(self):
        """Test wrapping response message with hook."""
        from application.agents.shared.hook_utils import wrap_response_with_hook

        hook = create_cloud_window_hook(
            conversation_id="test-conv-123",
            environment_status="deployed"
        )

        message = "Your environment is deployed and ready!"
        wrapped = wrap_response_with_hook(message, hook)

        # Parse wrapped response
        response_data = json.loads(wrapped)

        # Verify structure
        assert "message" in response_data
        assert "hook" in response_data
        assert response_data["message"] == message
        assert response_data["hook"]["type"] == "cloud_window"


class TestEnvironmentStatusValues:
    """Test suite for environment status values."""

    def test_deployed_status(self):
        """Test hook with 'deployed' status."""
        hook = create_cloud_window_hook(
            conversation_id="test-123",
            environment_status="deployed"
        )
        assert hook["data"]["environment_status"] == "deployed"

    def test_deploying_status(self):
        """Test hook with 'deploying' status."""
        hook = create_cloud_window_hook(
            conversation_id="test-123",
            environment_status="deploying"
        )
        assert hook["data"]["environment_status"] == "deploying"

    def test_not_deployed_status(self):
        """Test hook with 'not_deployed' status."""
        hook = create_cloud_window_hook(
            conversation_id="test-123",
            environment_status="not_deployed"
        )
        assert hook["data"]["environment_status"] == "not_deployed"

    def test_unknown_status(self):
        """Test hook with 'unknown' status."""
        hook = create_cloud_window_hook(
            conversation_id="test-123",
            environment_status="unknown"
        )
        assert hook["data"]["environment_status"] == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

