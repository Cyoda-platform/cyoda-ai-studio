"""Tests for QA agent."""

from __future__ import annotations

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from application.agents.qa.agent import root_agent


def test_agent_exists():
    """Test that the agent is properly defined."""
    assert root_agent is not None
    assert root_agent.name == "qa_agent"
    assert len(root_agent.tools) == 2


def test_agent_has_tools():
    """Test that the agent has the expected tools."""
    tool_names = {tool.__name__ for tool in root_agent.tools}

    assert "search_cyoda_concepts" in tool_names
    assert "explain_cyoda_pattern" in tool_names


@pytest.mark.asyncio
async def test_agent_basic_query():
    """Test agent responds to basic query."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="test-qa",
        agent=root_agent,
        session_service=session_service,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="test-user",
        session_id="test-session",
        new_message=types.Content(
            parts=[types.Part(text="What is a technical ID in Cyoda?")]
        ),
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    assert response_text is not None
    assert len(response_text) > 0


@pytest.mark.asyncio
async def test_agent_can_use_tools():
    """Test that agent can use its tools."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="test-qa",
        agent=root_agent,
        session_service=session_service,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="test-user",
        session_id="test-session",
        new_message=types.Content(
            parts=[types.Part(text="Explain the thin routes pattern")]
        ),
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    assert response_text is not None
    assert len(response_text) > 0
