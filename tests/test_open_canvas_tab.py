"""
Test suite for open_canvas_tab tool and create_open_canvas_tab_hook function.
"""

import pytest
from unittest.mock import MagicMock
from application.agents.shared.hook_utils import create_open_canvas_tab_hook


class TestCreateOpenCanvasTabHook:
    """Test create_open_canvas_tab_hook function."""

    def test_create_entities_tab_hook(self):
        """Test creating hook for entities tab."""
        hook = create_open_canvas_tab_hook(
            conversation_id="conv-123",
            tab_name="entities"
        )

        assert hook["type"] == "canvas_tab"
        assert hook["action"] == "open_canvas_tab"
        assert hook["data"]["conversation_id"] == "conv-123"
        assert hook["data"]["tab_name"] == "entities"
        assert "message" in hook["data"]

    def test_create_workflows_tab_hook(self):
        """Test creating hook for workflows tab."""
        hook = create_open_canvas_tab_hook(
            conversation_id="conv-456",
            tab_name="workflows"
        )

        assert hook["type"] == "canvas_tab"
        assert hook["data"]["tab_name"] == "workflows"
        assert "workflows" in hook["data"]["message"].lower()

    def test_create_requirements_tab_hook(self):
        """Test creating hook for requirements tab."""
        hook = create_open_canvas_tab_hook(
            conversation_id="conv-789",
            tab_name="requirements"
        )

        assert hook["type"] == "canvas_tab"
        assert hook["data"]["tab_name"] == "requirements"
        assert "requirements" in hook["data"]["message"].lower()

    def test_create_cloud_tab_hook(self):
        """Test creating hook for cloud tab."""
        hook = create_open_canvas_tab_hook(
            conversation_id="conv-cloud",
            tab_name="cloud"
        )

        assert hook["type"] == "canvas_tab"
        assert hook["data"]["tab_name"] == "cloud"
        assert "cloud" in hook["data"]["message"].lower()

    def test_custom_message(self):
        """Test creating hook with custom message."""
        custom_msg = "Custom message for entities"
        hook = create_open_canvas_tab_hook(
            conversation_id="conv-123",
            tab_name="entities",
            message=custom_msg
        )

        assert hook["data"]["message"] == custom_msg

    def test_invalid_tab_name(self):
        """Test that invalid tab_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_open_canvas_tab_hook(
                conversation_id="conv-123",
                tab_name="invalid_tab"
            )

        assert "Invalid tab_name" in str(exc_info.value)
        assert "invalid_tab" in str(exc_info.value)

    def test_all_valid_tabs(self):
        """Test that all valid tab names work."""
        valid_tabs = ["entities", "workflows", "requirements", "cloud"]

        for tab in valid_tabs:
            hook = create_open_canvas_tab_hook(
                conversation_id="conv-123",
                tab_name=tab
            )
            assert hook["data"]["tab_name"] == tab
            assert hook["type"] == "canvas_tab"


@pytest.mark.asyncio
async def test_open_canvas_tab_tool():
    """Test open_canvas_tab tool function."""
    from application.agents.github.tools import open_canvas_tab

    # Create mock tool context
    mock_context = MagicMock()
    mock_context.state = {
        "conversation_id": "conv-123"
    }

    # Test opening entities tab
    result = await open_canvas_tab(
        tab_name="entities",
        tool_context=mock_context
    )

    assert "✅" in result or "Opening" in result
    assert "last_tool_hook" in mock_context.state
    hook = mock_context.state["last_tool_hook"]
    assert hook["type"] == "canvas_tab"
    assert hook["data"]["tab_name"] == "entities"
    assert hook["action"] == "open_canvas_tab"


@pytest.mark.asyncio
async def test_open_canvas_tab_invalid_tab():
    """Test open_canvas_tab with invalid tab name."""
    from application.agents.github.tools import open_canvas_tab

    mock_context = MagicMock()
    mock_context.state = {
        "conversation_id": "conv-123"
    }

    result = await open_canvas_tab(
        tab_name="invalid",
        tool_context=mock_context
    )

    assert "ERROR" in result
    assert "Invalid tab_name" in result


@pytest.mark.asyncio
async def test_open_canvas_tab_no_context():
    """Test open_canvas_tab without tool context."""
    from application.agents.github.tools import open_canvas_tab

    result = await open_canvas_tab(
        tab_name="entities",
        tool_context=None
    )

    assert "ERROR" in result


@pytest.mark.asyncio
async def test_open_canvas_tab_no_conversation_id():
    """Test open_canvas_tab without conversation_id in context."""
    from application.agents.github.tools import open_canvas_tab

    mock_context = MagicMock()
    mock_context.state = {}

    result = await open_canvas_tab(
        tab_name="workflows",
        tool_context=mock_context
    )

    assert "ERROR" in result
    assert "conversation_id" in result

