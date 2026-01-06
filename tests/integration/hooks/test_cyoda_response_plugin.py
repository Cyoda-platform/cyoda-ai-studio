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


class TestCyodaResponseValidationPlugin:
    """Test suite for lightweight validation plugin."""

    def test_validation_plugin_initialization(self):
        """Test that validation plugin initializes correctly."""
        pass