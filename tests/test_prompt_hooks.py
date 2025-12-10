"""Tests for prompt-level hook creation."""

import pytest

from application.agents.shared.prompt_hook_factory import (
    create_prompt_hook,
    create_option_selection_hook,
    create_canvas_tab_hook,
)
from application.agents.shared.prompt_hook_helpers import (
    prompt_ask_user_choice,
    prompt_open_canvas,
    prompt_create_hook,
)
from application.agents.shared.hook_utils import wrap_response_with_hook


class TestPromptHookFactory:
    """Test prompt-level hook creation."""

    def test_create_option_selection_hook(self):
        """Test creating option selection hook from prompt."""
        hook = create_option_selection_hook(
            conversation_id="conv-123",
            question="What would you like to do?",
            options=[
                {"value": "deploy", "label": "🚀 Deploy"},
                {"value": "check", "label": "✅ Check"},
            ]
        )

        assert hook is not None
        assert hook["type"] == "option_selection"
        assert hook["parameters"]["question"] == "What would you like to do?"
        assert len(hook["parameters"]["options"]) == 2

    def test_create_canvas_tab_hook(self):
        """Test creating canvas tab hook from prompt."""
        hook = create_canvas_tab_hook(
            conversation_id="conv-123",
            tab_name="entities"
        )

        assert hook is not None
        assert hook["type"] == "canvas_tab"
        assert hook["parameters"]["tab_name"] == "entities"

    def test_create_prompt_hook_invalid(self):
        """Test creating invalid hook raises error."""
        with pytest.raises(ValueError, match="not registered"):
            create_prompt_hook(
                "invalid_hook",
                conversation_id="conv-123"
            )

    def test_wrap_option_selection_hook(self):
        """Test wrapping option selection hook in response."""
        hook = create_option_selection_hook(
            conversation_id="conv-123",
            question="Choose an option:",
            options=[
                {"value": "a", "label": "Option A"},
                {"value": "b", "label": "Option B"},
            ]
        )

        response = wrap_response_with_hook("Choose an action:", hook)
        assert "Choose an action:" in response
        assert "option_selection" in response


class TestPromptHookHelpers:
    """Test prompt hook helper functions."""

    def test_prompt_ask_user_choice(self):
        """Test prompt_ask_user_choice helper."""
        response = prompt_ask_user_choice(
            conversation_id="conv-123",
            question="What would you like?",
            options=[
                {"value": "a", "label": "Option A"},
                {"value": "b", "label": "Option B"},
            ],
            message="Choose an action:"
        )

        assert "Choose an action:" in response
        assert "option_selection" in response

    def test_prompt_open_canvas(self):
        """Test prompt_open_canvas helper."""
        response = prompt_open_canvas(
            conversation_id="conv-123",
            tab_name="workflows",
            message="Opening Canvas..."
        )

        assert "Opening Canvas..." in response
        assert "canvas_tab" in response

    def test_prompt_create_hook_generic(self):
        """Test generic prompt_create_hook helper."""
        response = prompt_create_hook(
            "option_selection",
            conversation_id="conv-123",
            message="Choose:",
            question="Pick one:",
            options=[{"value": "x", "label": "X"}]
        )

        assert "Choose:" in response
        assert "option_selection" in response

    def test_prompt_create_hook_invalid(self):
        """Test generic hook creation with invalid hook."""
        response = prompt_create_hook(
            "invalid_hook",
            conversation_id="conv-123",
            message="This should fail gracefully"
        )

        # Should return message without hook on error
        assert "This should fail gracefully" in response


class TestPromptHookIntegration:
    """Integration tests for prompt hooks."""

    def test_multiple_options_in_prompt(self):
        """Test prompt with multiple options."""
        options = [
            {"value": "deploy", "label": "🚀 Deploy"},
            {"value": "check", "label": "✅ Check"},
            {"value": "credentials", "label": "🔐 Credentials"},
        ]

        response = prompt_ask_user_choice(
            conversation_id="conv-123",
            question="What would you like to do?",
            options=options,
            message="I can help you with:"
        )

        assert "I can help you with:" in response
        assert "option_selection" in response

    def test_conditional_hook_creation(self):
        """Test creating different hooks based on context."""
        context = {"conversation_id": "conv-123", "has_environment": True}

        if context.get("has_environment"):
            response = prompt_ask_user_choice(
                conversation_id=context["conversation_id"],
                question="What's next?",
                options=[
                    {"value": "deploy_app", "label": "Deploy App"},
                    {"value": "view_logs", "label": "View Logs"},
                ]
            )
        else:
            response = prompt_ask_user_choice(
                conversation_id=context["conversation_id"],
                question="Create environment?",
                options=[
                    {"value": "deploy", "label": "Deploy"},
                ]
            )

        assert "option_selection" in response

