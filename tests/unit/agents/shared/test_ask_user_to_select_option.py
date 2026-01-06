"""Tests for ask_user_to_select_option function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.agents.shared.repository_tools.generation import ask_user_to_select_option


class TestAskUserToSelectOption:
    """Tests for ask_user_to_select_option function."""

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_with_valid_options(self):
        """Test with valid options provided."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"conversation_id": "conv-123"}
        
        options = [
            {"value": "opt1", "label": "Option 1"},
            {"value": "opt2", "label": "Option 2"}
        ]
        
        with patch("application.agents.shared.repository_tools.generation.create_option_selection_hook") as mock_hook:
            with patch("application.agents.shared.repository_tools.generation.wrap_response_with_hook") as mock_wrap:
                mock_hook.return_value = {"type": "option_selection"}
                mock_wrap.return_value = "Message with hook"
                
                result = await ask_user_to_select_option(
                    question="Choose an option",
                    options=options,
                    tool_context=mock_tool_context
                )
                
                assert result == "Message with hook"
                mock_hook.assert_called_once()
                mock_wrap.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_no_tool_context(self):
        """Test error when tool context is missing."""
        with pytest.raises(ValueError, match="Tool context not available"):
            await ask_user_to_select_option(
                question="Choose an option",
                options=[{"value": "opt1", "label": "Option 1"}],
                tool_context=None
            )

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_empty_question(self):
        """Test error when question is empty."""
        mock_tool_context = MagicMock()
        
        with pytest.raises(ValueError, match="question.*required"):
            await ask_user_to_select_option(
                question="",
                options=[{"value": "opt1", "label": "Option 1"}],
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_no_options(self):
        """Test error when options not provided."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"conversation_id": "conv-123"}

        with pytest.raises(ValueError, match="options.*required"):
            await ask_user_to_select_option(
                question="Choose an option",
                options=None,
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_empty_options_list(self):
        """Test error when options list is empty."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"conversation_id": "conv-123"}

        with pytest.raises(ValueError, match="options.*required"):
            await ask_user_to_select_option(
                question="Choose an option",
                options=[],
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_option_not_dict(self):
        """Test error when option is not a dictionary."""
        mock_tool_context = MagicMock()

        with pytest.raises(ValueError, match="not a dictionary"):
            await ask_user_to_select_option(
                question="Choose an option",
                options=["not_a_dict"],
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_missing_value_field(self):
        """Test error when option missing 'value' field."""
        mock_tool_context = MagicMock()

        with pytest.raises(ValueError, match="missing required 'value' field"):
            await ask_user_to_select_option(
                question="Choose an option",
                options=[{"label": "Option 1"}],
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_missing_label_field(self):
        """Test error when option missing 'label' field."""
        mock_tool_context = MagicMock()

        with pytest.raises(ValueError, match="missing required 'label' field"):
            await ask_user_to_select_option(
                question="Choose an option",
                options=[{"value": "opt1"}],
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_multiple_selection_type(self):
        """Test with multiple selection type."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"conversation_id": "conv-123"}
        
        options = [
            {"value": "opt1", "label": "Option 1"},
            {"value": "opt2", "label": "Option 2"}
        ]
        
        with patch("application.agents.shared.repository_tools.generation.create_option_selection_hook") as mock_hook:
            with patch("application.agents.shared.repository_tools.generation.wrap_response_with_hook") as mock_wrap:
                mock_hook.return_value = {"type": "option_selection"}
                mock_wrap.return_value = "Message with hook"
                
                result = await ask_user_to_select_option(
                    question="Choose options",
                    options=options,
                    selection_type="multiple",
                    tool_context=mock_tool_context
                )
                
                assert result == "Message with hook"
                call_args = mock_hook.call_args
                assert call_args[1]["selection_type"] == "multiple"

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_with_context(self):
        """Test with additional context parameter."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"conversation_id": "conv-123"}
        
        options = [{"value": "opt1", "label": "Option 1"}]
        
        with patch("application.agents.shared.repository_tools.generation.create_option_selection_hook") as mock_hook:
            with patch("application.agents.shared.repository_tools.generation.wrap_response_with_hook") as mock_wrap:
                mock_hook.return_value = {"type": "option_selection"}
                mock_wrap.return_value = "Message with hook"
                
                result = await ask_user_to_select_option(
                    question="Choose an option",
                    options=options,
                    context="Additional context",
                    tool_context=mock_tool_context
                )
                
                assert result == "Message with hook"
                call_args = mock_hook.call_args
                assert call_args[1]["context"] == "Additional context"

    @pytest.mark.asyncio
    async def test_ask_user_to_select_option_with_descriptions(self):
        """Test options with descriptions."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"conversation_id": "conv-123"}
        
        options = [
            {"value": "opt1", "label": "Option 1", "description": "First option"},
            {"value": "opt2", "label": "Option 2", "description": "Second option"}
        ]
        
        with patch("application.agents.shared.repository_tools.generation.create_option_selection_hook") as mock_hook:
            with patch("application.agents.shared.repository_tools.generation.wrap_response_with_hook") as mock_wrap:
                mock_hook.return_value = {"type": "option_selection"}
                mock_wrap.return_value = "Message with hook"
                
                result = await ask_user_to_select_option(
                    question="Choose an option",
                    options=options,
                    tool_context=mock_tool_context
                )
                
                assert result == "Message with hook"
                call_args = mock_hook.call_args
                assert call_args[1]["options"] == options

