"""Tests for Setup agent."""

from __future__ import annotations

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from application.agents.setup.agent import root_agent


def test_agent_exists():
    """Test that the agent is properly defined."""
    assert root_agent is not None
    assert root_agent.name == "setup_agent"
    assert len(root_agent.tools) == 11  # 3 original + 8 new tools


def test_agent_has_tools():
    """Test that the agent has the expected tools."""
    tool_names = {tool.__name__ for tool in root_agent.tools}

    # Original tools
    assert "validate_environment" in tool_names
    assert "check_project_structure" in tool_names
    assert "validate_workflow_file" in tool_names
    # New deployment & context tools
    assert "get_build_id_from_context" in tool_names
    assert "get_env_deploy_status" in tool_names
    assert "get_user_info" in tool_names
    # Credential management
    assert "ui_function_issue_technical_user" in tool_names
    # File operation tools
    assert "list_directory_files" in tool_names
    assert "read_file" in tool_names
    assert "add_application_resource" in tool_names
    # Workflow management
    assert "finish_discussion" in tool_names


@pytest.mark.asyncio
async def test_agent_basic_query():
    """Test agent responds to basic query."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="test-setup",
        agent=root_agent,
        session_service=session_service,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="test-user",
        session_id="test-session",
        new_message=types.Content(
            parts=[types.Part(text="What environment variables do I need for Cyoda?")]
        ),
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    assert response_text is not None
    assert len(response_text) > 0


@pytest.mark.asyncio
async def test_agent_can_use_tools(monkeypatch):
    """Test that agent can use its tools."""
    monkeypatch.setenv("CYODA_HOST", "localhost")

    session_service = InMemorySessionService()
    runner = Runner(
        app_name="test-setup",
        agent=root_agent,
        session_service=session_service,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="test-user",
        session_id="test-session",
        new_message=types.Content(
            parts=[types.Part(text="Check if CYODA_HOST environment variable is set")]
        ),
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    assert response_text is not None
    # The agent should have used the validate_environment tool
    assert len(response_text) > 0
