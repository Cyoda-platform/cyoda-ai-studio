"""
Tests for deployment hook functionality.

Verifies that deployment hooks are created correctly and include both
cloud window opening and deployment options.
"""

import json
import pytest
from application.agents.shared.hooks import (
    create_deployment_hook,
    create_deploy_and_open_cloud_hook,
    wrap_response_with_hook,
)


class TestDeploymentHook:
    """Test suite for deployment hook creation."""

    def test_create_deployment_hook_basic(self):
        """Test creating basic deployment hook."""
        hook = create_deployment_hook(
            conversation_id="conv-123"
        )

        assert hook["type"] == "option_selection"
        assert hook["action"] == "show_selection_ui"
        assert hook["data"]["conversation_id"] == "conv-123"
        assert "question" in hook["data"]
        assert "options" in hook["data"]
        assert len(hook["data"]["options"]) == 3

    def test_create_deployment_hook_with_environment_info(self):
        """Test creating deployment hook with environment details."""
        hook = create_deployment_hook(
            conversation_id="conv-123",
            environment_name="production",
            environment_url="https://client-user.cyoda.cloud"
        )

        assert hook["data"]["environment_name"] == "production"
        assert hook["data"]["environment_url"] == "https://client-user.cyoda.cloud"

    def test_deployment_hook_options(self):
        """Test that deployment hook has correct options."""
        hook = create_deployment_hook(
            conversation_id="conv-123"
        )

        options = hook["data"]["options"]
        option_values = [opt["value"] for opt in options]

        assert "deploy" in option_values
        assert "redeploy" in option_values
        assert "check_status" in option_values

    def test_deployment_hook_option_descriptions(self):
        """Test that deployment options have descriptions."""
        hook = create_deployment_hook(
            conversation_id="conv-123"
        )

        for option in hook["data"]["options"]:
            assert "label" in option
            assert "description" in option
            assert len(option["label"]) > 0
            assert len(option["description"]) > 0


class TestDeployAndOpenCloudHook:
    """Test suite for combined deploy and cloud window hook."""

    def test_create_deploy_and_open_cloud_hook_basic(self):
        """Test creating combined deploy and cloud hook."""
        hook = create_deploy_and_open_cloud_hook(
            conversation_id="conv-123"
        )

        assert hook["type"] == "combined"
        assert "hooks" in hook
        assert len(hook["hooks"]) == 2

    def test_deploy_and_open_cloud_hook_contains_cloud_window(self):
        """Test that combined hook includes cloud window hook."""
        hook = create_deploy_and_open_cloud_hook(
            conversation_id="conv-123"
        )

        cloud_hook = hook["hooks"][0]
        assert cloud_hook["type"] == "cloud_window"
        assert cloud_hook["action"] == "open_environments_panel"
        assert cloud_hook["data"]["conversation_id"] == "conv-123"

    def test_deploy_and_open_cloud_hook_contains_deployment_options(self):
        """Test that combined hook includes deployment options."""
        hook = create_deploy_and_open_cloud_hook(
            conversation_id="conv-123"
        )

        deployment_hook = hook["hooks"][1]
        assert deployment_hook["type"] == "option_selection"
        assert deployment_hook["action"] == "show_selection_ui"
        assert "options" in deployment_hook["data"]
        assert len(deployment_hook["data"]["options"]) == 3

    def test_deploy_and_open_cloud_hook_with_environment_info(self):
        """Test combined hook with environment details."""
        hook = create_deploy_and_open_cloud_hook(
            conversation_id="conv-123",
            environment_name="production",
            environment_url="https://client-user.cyoda.cloud"
        )

        cloud_hook = hook["hooks"][0]
        assert cloud_hook["data"]["environment_name"] == "production"
        assert cloud_hook["data"]["environment_url"] == "https://client-user.cyoda.cloud"

    def test_deploy_and_open_cloud_hook_cloud_message(self):
        """Test that cloud hook has deployment message."""
        hook = create_deploy_and_open_cloud_hook(
            conversation_id="conv-123"
        )

        cloud_hook = hook["hooks"][0]
        assert "message" in cloud_hook["data"]
        assert "Deploy" in cloud_hook["data"]["message"]

    def test_deploy_and_open_cloud_hook_serialization(self):
        """Test that combined hook can be serialized to JSON."""
        hook = create_deploy_and_open_cloud_hook(
            conversation_id="conv-123",
            environment_name="production"
        )

        # Serialize to JSON
        hook_json = json.dumps(hook)

        # Deserialize back
        hook_deserialized = json.loads(hook_json)

        # Verify structure is preserved
        assert hook_deserialized["type"] == "combined"
        assert len(hook_deserialized["hooks"]) == 2
        assert hook_deserialized["hooks"][0]["type"] == "cloud_window"
        assert hook_deserialized["hooks"][1]["type"] == "option_selection"


class TestHookWrapping:
    """Test suite for wrapping responses with hooks."""

    def test_wrap_response_with_deployment_hook(self):
        """Test wrapping response with deployment hook."""
        hook = create_deployment_hook(
            conversation_id="conv-123"
        )

        message = "Your application build is complete!"
        wrapped = wrap_response_with_hook(message, hook)

        # Parse wrapped response
        response_data = json.loads(wrapped)

        # Verify structure
        assert "message" in response_data
        assert "hook" in response_data
        assert response_data["message"] == message
        assert response_data["hook"]["type"] == "option_selection"

    def test_wrap_response_with_combined_hook(self):
        """Test wrapping response with combined hook."""
        hook = create_deploy_and_open_cloud_hook(
            conversation_id="conv-123"
        )

        message = "Build complete! Ready to deploy."
        wrapped = wrap_response_with_hook(message, hook)

        # Parse wrapped response
        response_data = json.loads(wrapped)

        # Verify structure
        assert "message" in response_data
        assert "hook" in response_data
        assert response_data["message"] == message
        assert response_data["hook"]["type"] == "combined"
        assert len(response_data["hook"]["hooks"]) == 2


class TestDeploymentWorkflow:
    """Test suite for deployment workflow."""

    def test_deployment_workflow_sequence(self):
        """Test the complete deployment workflow."""
        conversation_id = "conv-123"

        # Step 1: Create deployment hook
        deployment_hook = create_deploy_and_open_cloud_hook(
            conversation_id=conversation_id
        )

        # Verify hook structure
        assert deployment_hook["type"] == "combined"
        assert len(deployment_hook["hooks"]) == 2

        # Step 2: Wrap with message
        message = "Build complete! Ready to deploy."
        wrapped = wrap_response_with_hook(message, deployment_hook)

        # Verify wrapped response
        response_data = json.loads(wrapped)
        assert response_data["message"] == message
        assert response_data["hook"]["type"] == "combined"

        # Step 3: Verify UI can extract both hooks
        cloud_hook = response_data["hook"]["hooks"][0]
        deployment_options_hook = response_data["hook"]["hooks"][1]

        assert cloud_hook["type"] == "cloud_window"
        assert deployment_options_hook["type"] == "option_selection"

        # Step 4: Verify user can select deployment option
        options = deployment_options_hook["data"]["options"]
        assert any(opt["value"] == "deploy" for opt in options)
        assert any(opt["value"] == "redeploy" for opt in options)
        assert any(opt["value"] == "check_status" for opt in options)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

