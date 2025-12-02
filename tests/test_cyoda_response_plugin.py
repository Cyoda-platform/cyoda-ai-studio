"""
Tests for CyodaResponsePlugin to ensure non-empty responses.

These tests verify that the plugin correctly handles:
1. Empty responses (agent calls tools without generating text)
2. Tool execution summaries
3. Normal responses (plugin doesn't interfere)
"""

import pytest
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.events.event import Event
from google.adk.sessions.session import Session
from google.genai import types

from application.agents.shared.cyoda_response_plugin import (
    CyodaResponsePlugin,
    CyodaResponseValidationPlugin,
)


class TestCyodaResponsePlugin:
    """Test suite for CyodaResponsePlugin."""

    def test_plugin_initialization(self):
        """Test that plugin initializes with correct defaults."""
        plugin = CyodaResponsePlugin()
        
        assert plugin.name == "cyoda_response_plugin"
        assert plugin.provide_tool_summary is True
        assert plugin.default_message == "Task completed successfully."

    def test_plugin_custom_initialization(self):
        """Test that plugin accepts custom configuration."""
        plugin = CyodaResponsePlugin(
            name="custom_plugin",
            provide_tool_summary=False,
            default_message="Custom message",
        )
        
        assert plugin.name == "custom_plugin"
        assert plugin.provide_tool_summary is False
        assert plugin.default_message == "Custom message"

    @pytest.mark.asyncio
    async def test_empty_response_with_default_message(self):
        """Test that plugin provides default message when response is empty."""
        # Create plugin without tool summary
        plugin = CyodaResponsePlugin(provide_tool_summary=False)
        
        # Create mock session with no text events
        session = Session(
            id="test_session",
            app_name="test_app",
            user_id="test_user",
            events=[],
        )
        
        # Create mock callback context
        callback_context = CallbackContext(
            invocation_context=None,  # Not needed for this test
        )
        callback_context._session = session
        
        # Create mock agent
        agent = Agent(name="test_agent", model="gemini-2.0-flash")
        
        # Call the callback
        result = await plugin.after_agent_callback(
            agent=agent, callback_context=callback_context
        )
        
        # Should return default message
        assert result is not None
        assert result.role == "model"
        assert len(result.parts) == 1
        assert result.parts[0].text == "Task completed successfully."

    @pytest.mark.asyncio
    async def test_empty_response_with_tool_summary(self):
        """Test that plugin generates tool summary when response is empty."""
        # Create plugin with tool summary enabled
        plugin = CyodaResponsePlugin(provide_tool_summary=True)
        
        # Create mock events with function calls but no text
        events = [
            Event(
                id="event1",
                invocation_id="inv1",
                author="test_agent",
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="commit_and_push_changes",
                                args={},
                            )
                        )
                    ],
                ),
            )
        ]
        
        session = Session(
            id="test_session",
            app_name="test_app",
            user_id="test_user",
            events=events,
        )
        
        callback_context = CallbackContext(invocation_context=None)
        callback_context._session = session
        
        agent = Agent(name="test_agent", model="gemini-2.0-flash")
        
        # Call the callback
        result = await plugin.after_agent_callback(
            agent=agent, callback_context=callback_context
        )
        
        # Should return tool summary
        assert result is not None
        assert result.role == "model"
        assert len(result.parts) == 1
        assert "commit_and_push_changes" in result.parts[0].text
        assert "successfully" in result.parts[0].text.lower()

    @pytest.mark.asyncio
    async def test_multiple_tools_summary(self):
        """Test that plugin generates summary for multiple tools."""
        plugin = CyodaResponsePlugin(provide_tool_summary=True)
        
        # Create events with multiple function calls
        events = [
            Event(
                id="event1",
                invocation_id="inv1",
                author="test_agent",
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="create_branch", args={}
                            )
                        )
                    ],
                ),
            ),
            Event(
                id="event2",
                invocation_id="inv1",
                author="test_agent",
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="commit_changes", args={}
                            )
                        )
                    ],
                ),
            ),
            Event(
                id="event3",
                invocation_id="inv1",
                author="test_agent",
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="push_changes", args={}
                            )
                        )
                    ],
                ),
            ),
        ]
        
        session = Session(
            id="test_session",
            app_name="test_app",
            user_id="test_user",
            events=events,
        )
        
        callback_context = CallbackContext(invocation_context=None)
        callback_context._session = session
        
        agent = Agent(name="test_agent", model="gemini-2.0-flash")
        
        result = await plugin.after_agent_callback(
            agent=agent, callback_context=callback_context
        )
        
        # Should return summary with all tools
        assert result is not None
        text = result.parts[0].text
        assert "create_branch" in text
        assert "commit_changes" in text
        assert "push_changes" in text

    @pytest.mark.asyncio
    async def test_normal_response_not_modified(self):
        """Test that plugin doesn't interfere with normal text responses."""
        plugin = CyodaResponsePlugin()
        
        # Create events with text response
        events = [
            Event(
                id="event1",
                invocation_id="inv1",
                author="test_agent",
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="This is a normal response.")],
                ),
            )
        ]
        
        session = Session(
            id="test_session",
            app_name="test_app",
            user_id="test_user",
            events=events,
        )
        
        callback_context = CallbackContext(invocation_context=None)
        callback_context._session = session
        
        agent = Agent(name="test_agent", model="gemini-2.0-flash")
        
        result = await plugin.after_agent_callback(
            agent=agent, callback_context=callback_context
        )
        
        # Should return None (don't modify response)
        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_only_response_treated_as_empty(self):
        """Test that whitespace-only responses are treated as empty."""
        plugin = CyodaResponsePlugin(provide_tool_summary=False)
        
        # Create events with whitespace-only text
        events = [
            Event(
                id="event1",
                invocation_id="inv1",
                author="test_agent",
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="   \n\t  ")],  # Only whitespace
                ),
            )
        ]
        
        session = Session(
            id="test_session",
            app_name="test_app",
            user_id="test_user",
            events=events,
        )
        
        callback_context = CallbackContext(invocation_context=None)
        callback_context._session = session
        
        agent = Agent(name="test_agent", model="gemini-2.0-flash")
        
        result = await plugin.after_agent_callback(
            agent=agent, callback_context=callback_context
        )
        
        # Should provide default message
        assert result is not None
        assert result.parts[0].text == "Task completed successfully."


class TestCyodaResponseValidationPlugin:
    """Test suite for lightweight validation plugin."""

    @pytest.mark.asyncio
    async def test_validation_plugin_provides_default_message(self):
        """Test that validation plugin provides default message for empty response."""
        plugin = CyodaResponseValidationPlugin()
        
        session = Session(
            id="test_session",
            app_name="test_app",
            user_id="test_user",
            events=[],
        )
        
        callback_context = CallbackContext(invocation_context=None)
        callback_context._session = session
        
        agent = Agent(name="test_agent", model="gemini-2.0-flash")
        
        result = await plugin.after_agent_callback(
            agent=agent, callback_context=callback_context
        )
        
        assert result is not None
        assert result.parts[0].text == "Task completed successfully."

    @pytest.mark.asyncio
    async def test_validation_plugin_no_tool_summary(self):
        """Test that validation plugin doesn't generate tool summaries."""
        plugin = CyodaResponseValidationPlugin()
        
        # Create events with function calls
        events = [
            Event(
                id="event1",
                invocation_id="inv1",
                author="test_agent",
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="some_tool", args={}
                            )
                        )
                    ],
                ),
            )
        ]
        
        session = Session(
            id="test_session",
            app_name="test_app",
            user_id="test_user",
            events=events,
        )
        
        callback_context = CallbackContext(invocation_context=None)
        callback_context._session = session
        
        agent = Agent(name="test_agent", model="gemini-2.0-flash")
        
        result = await plugin.after_agent_callback(
            agent=agent, callback_context=callback_context
        )
        
        # Should return default message, not tool summary
        assert result is not None
        assert result.parts[0].text == "Task completed successfully."
        assert "some_tool" not in result.parts[0].text

