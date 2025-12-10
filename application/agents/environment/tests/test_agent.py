"""Tests for Environment Management agent."""

from __future__ import annotations

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from application.agents.environment.agent import root_agent


def test_agent_exists() -> None:
    """Test that the agent is properly defined."""
    assert root_agent is not None
    assert root_agent.name == "environment_agent"
    assert len(root_agent.tools) == 22


def test_agent_has_tools() -> None:
    """Test that the agent has the expected tools."""
    tool_names = {getattr(tool, "__name__", str(tool)) for tool in root_agent.tools}

    assert "check_environment_exists" in tool_names
    assert "deploy_cyoda_environment" in tool_names
    assert "deploy_user_application" in tool_names
    assert "get_deployment_status" in tool_names
    assert "get_build_logs" in tool_names
    assert "issue_technical_user" in tool_names


def test_agent_description() -> None:
    """Test that the agent has a proper description."""
    assert "environment" in root_agent.description.lower()
    assert "deployment" in root_agent.description.lower()


def test_agent_can_be_instantiated() -> None:
    """Test that the agent can be instantiated with a runner."""
    session_service = InMemorySessionService()  # type: ignore[no-untyped-call]
    runner = Runner(
        app_name="test-environment-agent",
        agent=root_agent,
        session_service=session_service,
    )

    assert runner is not None
    assert runner.agent == root_agent


def test_agent_instruction_exists() -> None:
    """Test that the agent has instruction template configured."""
    assert root_agent.instruction is not None


@pytest.mark.asyncio
async def test_issue_technical_user() -> None:
    """Test the credential issuance tool."""
    import json
    from unittest.mock import MagicMock

    from google.adk.tools.tool_context import ToolContext

    from application.agents.environment.tools import issue_technical_user

    # Create mock tool context
    mock_context = MagicMock(spec=ToolContext)
    mock_context.state = {"conversation_id": "test-conv-123"}

    result = await issue_technical_user(mock_context)

    # Verify error message (env_name is required)
    assert "ERROR" in result
    assert "env_name parameter is required" in result


@pytest.mark.asyncio
async def test_check_environment_exists_with_401() -> None:
    """Test that check_environment_exists correctly identifies existing environment when 401 is returned."""
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    from google.adk.tools.tool_context import ToolContext
    from common.exception.exceptions import InvalidTokenException

    from application.agents.environment.tools import check_environment_exists

    # Create mock tool context
    mock_context = MagicMock(spec=ToolContext)
    mock_context.state = {"user_id": "testuser", "conversation_id": "test-conv-123"}

    # Mock send_get_request to raise InvalidTokenException (simulating 401 response)
    with patch("common.utils.utils.send_get_request", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = InvalidTokenException("Unauthorized access")

        result = await check_environment_exists(mock_context, env_name="dev")

        # Parse the JSON result
        result_data = json.loads(result)

        # Verify that environment is detected as existing
        # The result is wrapped with "message" and "hook" at top level
        assert "message" in result_data
        assert "deployed and accessible" in result_data["message"]

        # Verify hook is included
        assert "hook" in result_data
        assert result_data["hook"]["type"] == "cloud_window"
        assert result_data["hook"]["action"] == "open_environments_panel"
        assert result_data["hook"]["data"]["conversation_id"] == "test-conv-123"


@pytest.mark.asyncio
async def test_check_environment_exists_with_other_exception() -> None:
    """Test that check_environment_exists correctly identifies non-existing environment when other exceptions occur."""
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    from google.adk.tools.tool_context import ToolContext

    from application.agents.environment.tools import check_environment_exists

    # Create mock tool context
    mock_context = MagicMock(spec=ToolContext)
    mock_context.state = {"user_id": "testuser"}

    # Mock send_get_request to raise a different exception (simulating connection error)
    with patch("common.utils.utils.send_get_request", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = Exception("Connection failed")

        result = await check_environment_exists(mock_context, env_name="dev")

        # Parse the JSON result
        result_data = json.loads(result)

        # Verify that environment is detected as not existing
        assert result_data["exists"] is False
        assert "testuser" in result_data["url"]
        assert "No Cyoda environment found" in result_data["message"]
