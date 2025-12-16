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
    assert len(root_agent.tools) == 0  # Setup agent is a guidance agent with no tools


@pytest.mark.asyncio
async def test_agent_basic_query():
    """Test agent responds to basic query."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="test-setup",
        agent=root_agent,
        session_service=session_service,
    )

    # Create session first
    await session_service.create_session(
        app_name="test-setup",
        user_id="test-user",
        session_id="test-session",
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
async def test_agent_provides_guidance():
    """Test that agent provides guidance without tools."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="test-setup",
        agent=root_agent,
        session_service=session_service,
    )

    # Create session first
    await session_service.create_session(
        app_name="test-setup",
        user_id="test-user",
        session_id="test-session",
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="test-user",
        session_id="test-session",
        new_message=types.Content(
            parts=[types.Part(text="I just built a Python Cyoda application, what do I do next?")]
        ),
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    assert response_text is not None
    # The agent should provide guidance about setup phases
    assert len(response_text) > 0
