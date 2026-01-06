"""Tests for ask_user_to_select_option with >=70% function coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAskUserToSelectOption:
    """Tests for ask_user_to_select_option achieving >=70% coverage."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create mock tool context."""
        context = MagicMock()
        context.state = {"conversation_id": "conv-123"}
        return context

    @pytest.mark.asyncio
    async def test_ask_user_no_tool_context(self):
        """Test when tool_context is not provided."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with pytest.raises(ValueError, match="Tool context not available"):
            await ask_user_to_select_option(
                question="Select option",
                options=[{"value": "opt1", "label": "Option 1"}],
                tool_context=None,
            )

    @pytest.mark.asyncio
    async def test_ask_user_empty_question(self, mock_tool_context):
        """Test when question is empty."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with pytest.raises(ValueError, match="question.*required"):
            await ask_user_to_select_option(
                question="",
                options=[{"value": "opt1", "label": "Option 1"}],
                tool_context=mock_tool_context,
            )

    @pytest.mark.asyncio
    async def test_ask_user_no_options(self, mock_tool_context):
        """Test when options list is empty."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        result = await ask_user_to_select_option(
            question="Select option",
            options=[],
            tool_context=mock_tool_context,
        )

        assert "options" in result.lower()
        assert "provide" in result.lower()

    @pytest.mark.asyncio
    async def test_ask_user_options_none(self, mock_tool_context):
        """Test when options is None."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        result = await ask_user_to_select_option(
            question="Select option",
            options=None,
            tool_context=mock_tool_context,
        )

        assert "options" in result.lower() or "provide" in result.lower()

    @pytest.mark.asyncio
    async def test_ask_user_option_not_dict(self, mock_tool_context):
        """Test when an option is not a dictionary."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        result = await ask_user_to_select_option(
            question="Select option",
            options=["not_a_dict"],
            tool_context=mock_tool_context,
        )

        assert "not a dictionary" in result
        assert "index 0" in result

    @pytest.mark.asyncio
    async def test_ask_user_option_missing_value(self, mock_tool_context):
        """Test when option is missing 'value' field."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        result = await ask_user_to_select_option(
            question="Select option",
            options=[{"label": "Option 1"}],
            tool_context=mock_tool_context,
        )

        assert "missing required 'value' field" in result

    @pytest.mark.asyncio
    async def test_ask_user_option_missing_label(self, mock_tool_context):
        """Test when option is missing 'label' field."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        result = await ask_user_to_select_option(
            question="Select option",
            options=[{"value": "opt1"}],
            tool_context=mock_tool_context,
        )

        assert "missing required 'label' field" in result

    @pytest.mark.asyncio
    async def test_ask_user_valid_single_option(self, mock_tool_context):
        """Test with valid single option."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                result = await ask_user_to_select_option(
                    question="Select option",
                    options=[{"value": "opt1", "label": "Option 1"}],
                    tool_context=mock_tool_context,
                )

                assert result == "message_with_hook"
                mock_hook_creator.assert_called_once()
                mock_wrap.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_user_multiple_options(self, mock_tool_context):
        """Test with multiple valid options."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                options = [
                    {"value": "opt1", "label": "Option 1"},
                    {"value": "opt2", "label": "Option 2"},
                    {"value": "opt3", "label": "Option 3"},
                ]

                result = await ask_user_to_select_option(
                    question="Select option",
                    options=options,
                    tool_context=mock_tool_context,
                )

                assert result == "message_with_hook"
                call_kwargs = mock_hook_creator.call_args[1]
                assert call_kwargs["options"] == options

    @pytest.mark.asyncio
    async def test_ask_user_with_description(self, mock_tool_context):
        """Test option with description field."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                result = await ask_user_to_select_option(
                    question="Select option",
                    options=[
                        {
                            "value": "opt1",
                            "label": "Option 1",
                            "description": "This is option 1",
                        }
                    ],
                    tool_context=mock_tool_context,
                )

                assert result == "message_with_hook"

    @pytest.mark.asyncio
    async def test_ask_user_selection_type_single(self, mock_tool_context):
        """Test with selection_type='single'."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                await ask_user_to_select_option(
                    question="Select option",
                    options=[{"value": "opt1", "label": "Option 1"}],
                    selection_type="single",
                    tool_context=mock_tool_context,
                )

                call_kwargs = mock_hook_creator.call_args[1]
                assert call_kwargs["selection_type"] == "single"

    @pytest.mark.asyncio
    async def test_ask_user_selection_type_multiple(self, mock_tool_context):
        """Test with selection_type='multiple'."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                await ask_user_to_select_option(
                    question="Select options",
                    options=[{"value": "opt1", "label": "Option 1"}],
                    selection_type="multiple",
                    tool_context=mock_tool_context,
                )

                call_kwargs = mock_hook_creator.call_args[1]
                assert call_kwargs["selection_type"] == "multiple"

    @pytest.mark.asyncio
    async def test_ask_user_with_context_param(self, mock_tool_context):
        """Test with context parameter."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                await ask_user_to_select_option(
                    question="Select option",
                    options=[{"value": "opt1", "label": "Option 1"}],
                    context="Some context information",
                    tool_context=mock_tool_context,
                )

                call_kwargs = mock_hook_creator.call_args[1]
                assert call_kwargs["context"] == "Some context information"

    @pytest.mark.asyncio
    async def test_ask_user_conversation_id_from_context(self, mock_tool_context):
        """Test that conversation_id is extracted from tool_context.state."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        mock_tool_context.state = {"conversation_id": "conv-456"}

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                await ask_user_to_select_option(
                    question="Select option",
                    options=[{"value": "opt1", "label": "Option 1"}],
                    tool_context=mock_tool_context,
                )

                call_kwargs = mock_hook_creator.call_args[1]
                assert call_kwargs["conversation_id"] == "conv-456"

    @pytest.mark.asyncio
    async def test_ask_user_hook_stored_in_context(self, mock_tool_context):
        """Test that hook is stored in tool_context.state."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                await ask_user_to_select_option(
                    question="Select option",
                    options=[{"value": "opt1", "label": "Option 1"}],
                    tool_context=mock_tool_context,
                )

                assert mock_tool_context.state["last_tool_hook"] == mock_hook

    @pytest.mark.asyncio
    async def test_ask_user_response_message_format(self, mock_tool_context):
        """Test that response message contains expected content."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "wrapped_message"

                await ask_user_to_select_option(
                    question="Select your preference",
                    options=[{"value": "opt1", "label": "Option 1"}],
                    tool_context=mock_tool_context,
                )

                # Check that wrap_response_with_hook was called with expected message
                call_args = mock_wrap.call_args[0]
                message = call_args[0]
                assert "Select your preference" in message
                assert "Please select your choice(s)" in message

    @pytest.mark.asyncio
    async def test_ask_user_multiple_validation_errors_first_error_returned(
        self, mock_tool_context
    ):
        """Test that first validation error is returned."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        # Option missing both value and label - should report first error (not dict)
        result = await ask_user_to_select_option(
            question="Select option",
            options=[123],  # Not a dict
            tool_context=mock_tool_context,
        )

        assert "not a dictionary" in result

    @pytest.mark.asyncio
    async def test_ask_user_empty_question_string_vs_none(self, mock_tool_context):
        """Test that empty string is treated differently from None."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        # Empty string should raise ValueError
        with pytest.raises(ValueError):
            await ask_user_to_select_option(
                question="",
                options=[{"value": "opt1", "label": "Option 1"}],
                tool_context=mock_tool_context,
            )

    @pytest.mark.asyncio
    async def test_ask_user_with_special_characters_in_question(
        self, mock_tool_context
    ):
        """Test question with special characters."""
        from application.agents.shared.repository_tools.generation import (
            ask_user_to_select_option,
        )

        with patch(
            "application.agents.shared.repository_tools.generation.create_option_selection_hook"
        ) as mock_hook_creator:
            with patch(
                "application.agents.shared.repository_tools.generation.wrap_response_with_hook"
            ) as mock_wrap:
                mock_hook = MagicMock()
                mock_hook_creator.return_value = mock_hook
                mock_wrap.return_value = "message_with_hook"

                question = "Select \"your choice\" & confirm?"
                await ask_user_to_select_option(
                    question=question,
                    options=[{"value": "opt1", "label": "Option 1"}],
                    tool_context=mock_tool_context,
                )

                call_kwargs = mock_hook_creator.call_args[1]
                assert call_kwargs["question"] == question
