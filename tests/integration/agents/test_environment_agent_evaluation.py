"""
Environment Agent Evaluation Tests

Tests the environment agent's credential issuance functionality.

Run with:
    pytest tests/integration/agents/test_environment_agent_evaluation.py -v -s
"""

import json
from pathlib import Path

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


# Base path for test files
EVALS_DIR = Path(__file__).parent.parent.parent.parent / "application" / "agents" / "environment" / "evals"


class TestEnvironmentAgentCredentials:
    """Test environment agent credential issuance functionality."""
    
    @pytest.mark.asyncio
    async def test_credential_issuance(self):
        """Test environment agent with credential issuance scenarios."""
        result = await AgentEvaluator.evaluate(
            agent_module="application.agents.environment",
            eval_dataset_file_path_or_dir=str(EVALS_DIR / "issue_credentials.test.json"),
        )
        
        # Verify evaluation completed
        assert result is not None
        print(f"\n✓ Environment Agent Credential Issuance Evaluation Results:\n{result}")


class TestEnvironmentAgentToolOutput:
    """Test that ui_function_issue_technical_user updates conversation correctly."""

    @pytest.mark.asyncio
    async def test_tool_stores_ui_function_in_context(self):
        """Verify the tool stores UI function in context instead of directly updating conversation."""
        from unittest.mock import MagicMock
        from google.adk.tools.tool_context import ToolContext
        from application.agents.environment.tools import ui_function_issue_technical_user

        # Create mock tool context
        mock_context = MagicMock(spec=ToolContext)
        mock_context.state = {}

        # Call the tool
        result = await ui_function_issue_technical_user(mock_context)

        # Verify it's a string
        assert isinstance(result, str), "Tool should return a string"

        # Verify success message
        assert "✅" in result
        assert "Credential issuance initiated" in result

        # Verify UI function was stored in context (not directly in conversation)
        assert "ui_functions" in mock_context.state, "Should store ui_functions in context"
        assert len(mock_context.state["ui_functions"]) == 1, "Should have one UI function"

        # Parse the UI function from context
        ui_func = mock_context.state["ui_functions"][0]

        # Verify structure
        assert ui_func["type"] == "ui_function", "Missing or incorrect 'type' field"
        assert ui_func["function"] == "ui_function_issue_technical_user", "Missing or incorrect 'function' field"
        assert ui_func["method"] == "POST", "Missing or incorrect 'method' field"
        assert ui_func["path"] == "/api/users", "Missing or incorrect 'path' field"
        assert ui_func["response_format"] == "json", "Missing or incorrect 'response_format' field"

        print(f"\n✅ Tool stores UI function in context (to be added by route handler):")
        print(json.dumps(ui_func, indent=2))


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async test"
    )


if __name__ == "__main__":
    # Allow running directly with: python test_environment_agent_evaluation.py
    pytest.main([__file__, "-v", "-s"])

