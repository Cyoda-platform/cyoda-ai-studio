"""Tests for parameter validation in repository tools."""

from unittest.mock import MagicMock

import pytest
from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools import (
    clone_repository,
    generate_application,
    save_files_to_branch,
    set_repository_config,
)


class TestSetRepositoryConfigValidation:
    """Test parameter validation for set_repository_config."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context."""
        context = MagicMock(spec=ToolContext)
        context.state = {}
        return context

    @pytest.mark.asyncio
    async def test_missing_repository_type_raises_error(self, mock_tool_context):
        """Test that missing repository_type raises ValueError."""
        with pytest.raises(ValueError, match="repository_type.*required"):
            await set_repository_config(
                repository_type="",
                tool_context=mock_tool_context,
            )

    @pytest.mark.asyncio
    async def test_invalid_repository_type_raises_error(self, mock_tool_context):
        """Test that invalid repository_type raises ValueError."""
        with pytest.raises(ValueError, match="must be 'public' or 'private'"):
            await set_repository_config(
                repository_type="invalid",
                tool_context=mock_tool_context,
            )

    @pytest.mark.asyncio
    async def test_private_repo_missing_installation_id_raises_error(
        self, mock_tool_context
    ):
        """Test that private repo without installation_id raises ValueError."""
        with pytest.raises(ValueError, match="installation_id.*required"):
            await set_repository_config(
                repository_type="private",
                repository_url="https://github.com/owner/repo",
                tool_context=mock_tool_context,
            )

    @pytest.mark.asyncio
    async def test_private_repo_missing_repository_url_raises_error(
        self, mock_tool_context
    ):
        """Test that private repo without repository_url raises ValueError."""
        with pytest.raises(ValueError, match="repository_url.*required"):
            await set_repository_config(
                repository_type="private",
                installation_id="12345",
                tool_context=mock_tool_context,
            )


class TestGenerateApplicationValidation:
    """Test parameter validation for generate_application."""

    @pytest.mark.asyncio
    async def test_missing_requirements_raises_error(self):
        """Test that missing requirements raises ValueError."""
        # Validation happens at function entry, before async code
        with pytest.raises(ValueError, match="requirements.*required"):
            await generate_application(requirements="")


class TestSaveFilesToBranchValidation:
    """Test parameter validation for save_files_to_branch."""

    @pytest.mark.asyncio
    async def test_missing_files_raises_error(self):
        """Test that missing files raises ValueError."""
        # Validation happens at function entry, before async code
        with pytest.raises(ValueError, match="files.*required"):
            await save_files_to_branch(files=[])

    @pytest.mark.asyncio
    async def test_file_missing_filename_raises_error(self):
        """Test that file missing 'filename' raises ValueError."""
        # Validation happens at function entry, before async code
        with pytest.raises(ValueError, match="missing required 'filename' field"):
            await save_files_to_branch(files=[{"content": "test"}])

    @pytest.mark.asyncio
    async def test_file_missing_content_raises_error(self):
        """Test that file missing 'content' raises ValueError."""
        # Validation happens at function entry, before async code
        with pytest.raises(ValueError, match="missing required 'content' field"):
            await save_files_to_branch(files=[{"filename": "test.txt"}])
