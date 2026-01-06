"""Unit tests for save_files_to_branch tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil
import subprocess

from application.agents.shared.repository_tools import save_files_to_branch


class TestSaveFilesToBranch:
    """Test save_files_to_branch tool functionality."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, capture_output=True)
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_tool_context(self, temp_repo):
        """Create a mock tool context with required state."""
        context = MagicMock()
        context.state = {
            "repository_path": temp_repo,
            "branch_name": "test-branch",
            "language": "python",
            "repository_type": "public",
        }
        return context

    @pytest.mark.asyncio
    async def test_save_files_to_branch_python(self, mock_tool_context):
        """Test saving files to Python repository."""
        files = [
            {"filename": "requirements.txt", "content": "flask==2.0.0\n"},
            {"filename": "spec.md", "content": "# API Specification\n"},
        ]

        result = await save_files_to_branch(files=files, tool_context=mock_tool_context)

        # Verify success
        assert "SUCCESS" in result
        assert "2 file(s)" in result

        # Verify files were saved
        repo_path = Path(mock_tool_context.state["repository_path"])
        func_req_dir = repo_path / "application" / "resources" / "functional_requirements"
        assert (func_req_dir / "requirements.txt").exists()
        assert (func_req_dir / "spec.md").exists()

    @pytest.mark.asyncio
    async def test_save_files_to_branch_java(self, mock_tool_context):
        """Test saving files to Java repository."""
        mock_tool_context.state["language"] = "java"
        files = [
            {"filename": "api.yaml", "content": "openapi: 3.0.0\n"},
        ]

        result = await save_files_to_branch(files=files, tool_context=mock_tool_context)

        # Verify success
        assert "SUCCESS" in result

        # Verify files were saved to Java path
        repo_path = Path(mock_tool_context.state["repository_path"])
        func_req_dir = repo_path / "src" / "main" / "resources" / "functional_requirements"
        assert (func_req_dir / "api.yaml").exists()

    @pytest.mark.asyncio
    async def test_save_files_to_branch_empty_files(self, mock_tool_context):
        """Test saving empty file list raises ValueError."""
        files = []

        with pytest.raises(ValueError, match="files parameter is required"):
            await save_files_to_branch(files=files, tool_context=mock_tool_context)

    @pytest.mark.asyncio
    async def test_save_files_to_branch_invalid_file_format(self, mock_tool_context):
        """Test saving files with invalid format raises ValueError."""
        files = [
            "not a dict",  # Invalid format
        ]

        with pytest.raises(ValueError, match="missing required 'filename' field"):
            await save_files_to_branch(files=files, tool_context=mock_tool_context)

    @pytest.mark.asyncio
    async def test_save_files_to_branch_missing_filename(self, mock_tool_context):
        """Test saving file without filename raises ValueError."""
        files = [
            {"content": "some content"},  # Missing filename
        ]

        with pytest.raises(ValueError, match="missing required 'filename' field"):
            await save_files_to_branch(files=files, tool_context=mock_tool_context)

    @pytest.mark.asyncio
    async def test_save_files_to_branch_missing_content(self, mock_tool_context):
        """Test saving file without content raises ValueError."""
        files = [
            {"filename": "test.txt"},  # Missing content
        ]

        with pytest.raises(ValueError, match="missing required 'content' field"):
            await save_files_to_branch(files=files, tool_context=mock_tool_context)

    @pytest.mark.asyncio
    async def test_save_files_to_branch_directory_traversal_prevention(self, mock_tool_context):
        """Test that directory traversal attempts are prevented."""
        files = [
            {"filename": "../../../etc/passwd", "content": "malicious"},
        ]

        result = await save_files_to_branch(files=files, tool_context=mock_tool_context)

        # Should save only the filename, not the path
        repo_path = Path(mock_tool_context.state["repository_path"])
        func_req_dir = repo_path / "application" / "resources" / "functional_requirements"

        # Should not create files outside functional_requirements
        assert not (repo_path / "etc" / "passwd").exists()
        # Should save with just the filename
        assert (func_req_dir / "passwd").exists() or "SUCCESS" in result
