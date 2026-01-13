import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from application.agents.shared.cyoda_response_plugin import (
    CyodaResponsePlugin,
    CyodaResponseValidationPlugin,
)


@pytest.fixture
def mock_callback_context():
    """Fixture for a mock CallbackContext."""
    mock_context = MagicMock(spec=CallbackContext)
    mock_context.session.events = []
    mock_context.state = {}
    return mock_context


@pytest.fixture
def mock_base_agent():
    """Fixture for a mock BaseAgent."""
    return MagicMock(spec=BaseAgent)


@pytest.fixture(autouse=True)
def setup_logging():
    """Ensures logging is captured during tests."""
    logging.disable(logging.NOTSET)  # Enable logging for tests


class TestCyodaResponsePlugin:
    """Tests for CyodaResponsePlugin."""

    @pytest.mark.asyncio
    async def test_text_response_present(self, mock_base_agent, mock_callback_context):
        """
        Tests that if a text response is present, the plugin returns None.
        """
        # Arrange
        plugin = CyodaResponsePlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="model", parts=[types.Part(text="Hello world")]
                )
            )
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_no_text_response_with_tool_calls(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests that if no text response is present but tool calls are,
        a summary is generated.
        """
        # Arrange
        plugin = CyodaResponsePlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="tool1", args={}, id="1"
                            )
                        )
                    ],
                )
            ),
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="tool2", args={}, id="2"
                            )
                        )
                    ],
                )
            ),
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert result.role == "model"
        assert len(result.parts) == 1
        assert result.parts[0].text == "Executed the following tools: tool1 and tool2."

    @pytest.mark.asyncio
    async def test_no_text_response_no_tool_calls(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests that if no text response or tool calls are present,
        the default message is returned.
        """
        # Arrange
        plugin = CyodaResponsePlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(role="model", parts=[types.Part(text="")])
            )  # Empty text part
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert result.role == "model"
        assert len(result.parts) == 1
        assert result.parts[0].text == "Task completed successfully."

    @pytest.mark.asyncio
    async def test_hook_logging(self, mock_base_agent, mock_callback_context, caplog):
        """
        Tests that hook information is logged if present in the state.
        """
        # Arrange
        plugin = CyodaResponsePlugin()
        mock_callback_context.state = {"last_tool_hook": {"type": "test_hook"}}
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="model", parts=[types.Part(text="Hello world")]
                )
            )
        ]

        # Act
        with caplog.at_level(logging.INFO):
            await plugin.after_agent_callback(
                agent=mock_base_agent, callback_context=mock_callback_context
            )

        # Assert
        assert "Hook found in session state: test_hook" in caplog.text

    @pytest.mark.asyncio
    async def test_multiple_unique_tool_calls(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests correct summary for multiple unique tools.
        """
        # Arrange
        plugin = CyodaResponsePlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="toolA", args={}, id="a1"
                            )
                        )
                    ],
                )
            ),
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="toolB", args={}, id="b1"
                            )
                        )
                    ],
                )
            ),
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="toolC", args={}, id="c1"
                            )
                        )
                    ],
                )
            ),
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert (
            result.parts[0].text
            == "Executed the following tools: toolA, toolB and toolC."
        )

    @pytest.mark.asyncio
    async def test_multiple_duplicate_tool_calls(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests correct summary for multiple duplicate tool calls (should list unique names).
        """
        # Arrange
        plugin = CyodaResponsePlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="toolA", args={}, id="a1"
                            )
                        )
                    ],
                )
            ),
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="toolB", args={}, id="b1"
                            )
                        )
                    ],
                )
            ),
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="toolA", args={}, id="a2"
                            )
                        )
                    ],
                )
            ),
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert result.parts[0].text == "Executed the following tools: toolA and toolB."

    @pytest.mark.asyncio
    async def test_no_summary_if_disabled(self, mock_base_agent, mock_callback_context):
        """
        Tests that no tool summary is provided if provide_tool_summary is False.
        """
        # Arrange
        plugin = CyodaResponsePlugin(provide_tool_summary=False)
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="tool1", args={}, id="1"
                            )
                        )
                    ],
                )
            )
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert result.parts[0].text == "Task completed successfully."


class TestCyodaResponseValidationPlugin:
    """Tests for CyodaResponseValidationPlugin."""

    @pytest.mark.asyncio
    async def test_validation_text_response_present(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests that if a text response is present, the plugin returns None.
        """
        # Arrange
        plugin = CyodaResponseValidationPlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="model", parts=[types.Part(text="Hello world")]
                )
            )
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_validation_no_text_response(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests that if no text response is present, the default message is returned.
        """
        # Arrange
        plugin = CyodaResponseValidationPlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(role="model", parts=[types.Part(text="")])
            )  # Empty text part
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert result.role == "model"
        assert len(result.parts) == 1
        assert result.parts[0].text == "Task completed successfully."

    @pytest.mark.asyncio
    async def test_validation_no_content_at_all(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests that if no content is found in events, the default message is returned.
        """
        # Arrange
        plugin = CyodaResponseValidationPlugin()
        mock_callback_context.session.events = [
            MagicMock(content=None)  # No content at all
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert result.role == "model"
        assert len(result.parts) == 1
        assert result.parts[0].text == "Task completed successfully."

    @pytest.mark.asyncio
    async def test_validation_non_model_role_content(
        self, mock_base_agent, mock_callback_context
    ):
        """
        Tests that content with a non-model role is ignored.
        """
        # Arrange
        plugin = CyodaResponseValidationPlugin()
        mock_callback_context.session.events = [
            MagicMock(
                content=types.Content(
                    role="user", parts=[types.Part(text="User input")]
                )
            )
        ]

        # Act
        result = await plugin.after_agent_callback(
            agent=mock_base_agent, callback_context=mock_callback_context
        )

        # Assert
        assert isinstance(result, types.Content)
        assert result.parts[0].text == "Task completed successfully."
