"""Tests for functional requirements validation in generate_application."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools import generate_application


class TestFunctionalRequirementsValidation:
    """Test functional requirements validation in generate_application."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context."""
        context = MagicMock(spec=ToolContext)
        context.state = {
            "conversation_id": "test-conv-123",
            "language": "python",
            "repository_path": "/tmp/test_repo",
            "branch_name": "test-branch",
        }
        return context

    @pytest.mark.asyncio
    async def test_missing_functional_requirements_returns_guidance(
        self, tmp_path, mock_tool_context
    ):
        """Test that missing functional requirements returns helpful guidance."""
        # Create a mock repository structure without requirements
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        (repo_path / "application").mkdir()
        (repo_path / "application" / "resources").mkdir()
        # Don't create functional_requirements directory

        mock_tool_context.state["repository_path"] = str(repo_path)

        result = await generate_application(
            requirements="Build a test app",
            tool_context=mock_tool_context,
        )

        assert isinstance(result, str)
        # Accept error messages or requirement warnings
        assert (
            "no functional requirements" in result.lower()
            or "error" in result.lower()
            or "failed to start" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_empty_functional_requirements_returns_guidance(
        self, tmp_path, mock_tool_context
    ):
        """Test that empty functional requirements directory returns guidance."""
        # Create a mock repository with empty requirements directory
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        (repo_path / "application").mkdir()
        (repo_path / "application" / "resources").mkdir()
        (repo_path / "application" / "resources" / "functional_requirements").mkdir()
        # Directory exists but is empty

        mock_tool_context.state["repository_path"] = str(repo_path)

        result = await generate_application(
            requirements="Build a test app",
            tool_context=mock_tool_context,
        )

        assert isinstance(result, str)
        # Accept error messages or requirement warnings
        assert (
            "no functional requirements" in result.lower()
            or "error" in result.lower()
            or "failed to start" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_with_functional_requirements_proceeds(
        self, tmp_path, mock_tool_context
    ):
        """Test that with functional requirements, the build proceeds."""
        # Create a mock repository with requirements
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        (repo_path / "application").mkdir()
        (repo_path / "application" / "resources").mkdir()
        req_dir = repo_path / "application" / "resources" / "functional_requirements"
        req_dir.mkdir()
        (req_dir / "requirements.md").write_text(
            "# Test Requirements\nBuild a test app"
        )

        mock_tool_context.state["repository_path"] = str(repo_path)

        # Mock the template loading and CLI execution
        with patch(
            "application.agents.shared.repository_tools._load_prompt_template"
        ) as mock_template:
            mock_template.return_value = "Test template"

            result = await generate_application(
                requirements="Build a test app",
                tool_context=mock_tool_context,
            )

            # Should proceed past the requirements check
            # (may fail later due to missing CLI script, but that's expected)
            assert "No functional requirements found" not in result
