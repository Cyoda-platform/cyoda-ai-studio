"""Unit tests for save_file_to_repository tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from application.agents.github.tools import save_file_to_repository


class TestSaveFileToRepository:
    """Test save_file_to_repository tool functionality."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository directory with .git folder."""
        temp_dir = tempfile.mkdtemp()
        # Create .git directory to mark it as a git repository
        git_dir = Path(temp_dir) / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_tool_context(self, temp_repo):
        """Create a mock tool context."""
        context = MagicMock()
        context.state = {
            "repository_path": temp_repo,
            "conversation_id": "conv-123",
        }
        return context

    @pytest.mark.asyncio
    async def test_save_entity_file_creates_hook(self, mock_tool_context):
        """Test saving an entity file creates canvas tab hook."""
        file_path = "application/resources/entity/customer/version_1/customer.json"
        content = '{"id": "CUST-001", "name": "John Doe", "email": "john@example.com"}'

        result = await save_file_to_repository(
            file_path=file_path,
            content=content,
            tool_context=mock_tool_context,
        )

        # Verify file was saved
        full_path = Path(mock_tool_context.state["repository_path"]) / file_path
        assert full_path.exists()
        assert full_path.read_text() == content

        # Verify hook was created
        assert "last_tool_hook" in mock_tool_context.state
        hook = mock_tool_context.state["last_tool_hook"]
        assert hook["type"] == "canvas_tab"
        assert hook["data"]["tab_name"] == "entities"
        # Result is wrapped with hook, so check for message content
        assert "File saved" in result or "Entities" in result

    @pytest.mark.asyncio
    async def test_save_workflow_file_creates_hook(self, mock_tool_context):
        """Test saving a workflow file creates canvas tab hook."""
        file_path = "application/resources/workflow/customer/version_1/customer.json"
        content = '{"name": "CustomerWorkflow"}'

        result = await save_file_to_repository(
            file_path=file_path,
            content=content,
            tool_context=mock_tool_context,
        )

        # Verify hook was created for workflows
        hook = mock_tool_context.state["last_tool_hook"]
        assert hook["data"]["tab_name"] == "workflows"
        assert "Workflows" in result

    @pytest.mark.asyncio
    async def test_save_requirement_file_creates_hook(self, mock_tool_context):
        """Test saving a requirement file creates canvas tab hook."""
        file_path = "application/resources/functional_requirements/spec.md"
        content = "# Requirements"

        result = await save_file_to_repository(
            file_path=file_path,
            content=content,
            tool_context=mock_tool_context,
        )

        # Verify hook was created for requirements
        hook = mock_tool_context.state["last_tool_hook"]
        assert hook["data"]["tab_name"] == "requirements"
        assert "Requirements" in result

    @pytest.mark.asyncio
    async def test_save_non_canvas_file_no_hook(self, mock_tool_context):
        """Test saving a non-canvas file doesn't create hook."""
        file_path = "application/config/settings.json"
        content = '{"setting": "value"}'

        result = await save_file_to_repository(
            file_path=file_path,
            content=content,
            tool_context=mock_tool_context,
        )

        # Verify file was saved
        full_path = Path(mock_tool_context.state["repository_path"]) / file_path
        assert full_path.exists()

        # Verify no hook was created
        assert "last_tool_hook" not in mock_tool_context.state
        assert "SUCCESS" in result

    @pytest.mark.asyncio
    async def test_save_file_no_conversation_id(self, temp_repo):
        """Test saving entity file without conversation_id doesn't create hook."""
        context = MagicMock()
        context.state = {"repository_path": temp_repo}  # No conversation_id

        file_path = "application/resources/entity/customer/version_1/customer.json"
        content = '{"name": "Customer"}'

        result = await save_file_to_repository(
            file_path=file_path,
            content=content,
            tool_context=context,
        )

        # File should still be saved
        full_path = Path(temp_repo) / file_path
        assert full_path.exists()

        # But no hook should be created
        assert "last_tool_hook" not in context.state
        assert "SUCCESS" in result

    @pytest.mark.asyncio
    async def test_save_file_no_repository_path(self):
        """Test saving file without repository_path returns error."""
        context = MagicMock()
        context.state = {}  # No repository_path

        result = await save_file_to_repository(
            file_path="test.json",
            content="{}",
            tool_context=context,
        )

        assert "ERROR" in result
        assert "repository_path" in result

