"""Tests for repository endpoints functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from application.routes.repository_endpoints.helpers import ensure_repository_cloned


class TestEnsureRepositoryCloned:
    """Test ensure_repository_cloned function."""

    @pytest.mark.asyncio
    async def test_ensure_repository_already_exists(self):
        """Test function returns success when repository already exists."""
        with patch("pathlib.Path.exists", return_value=True):
            success, message, path = await ensure_repository_cloned(
                repository_url="https://github.com/test/repo",
                repository_branch="main"
            )
            assert success is True
            assert path is not None

    @pytest.mark.asyncio
    async def test_ensure_repository_clone_success(self):
        """Test successful repository cloning."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    success, message, path = await ensure_repository_cloned(
                        repository_url="https://github.com/test/repo",
                        repository_branch="main"
                    )
                    assert success is True

    @pytest.mark.asyncio
    async def test_ensure_repository_clone_failure(self):
        """Test repository cloning failure."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 1
                    mock_result.stderr = "Clone failed"
                    mock_run.return_value = mock_result
                    
                    success, message, path = await ensure_repository_cloned(
                        repository_url="https://github.com/test/repo",
                        repository_branch="main"
                    )
                    assert success is False
                    assert "ERROR" in message or "Failed" in message

    @pytest.mark.asyncio
    async def test_ensure_repository_with_installation_id(self):
        """Test repository cloning with installation_id."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    success, message, path = await ensure_repository_cloned(
                        repository_url="https://github.com/test/repo",
                        repository_branch="main",
                        installation_id="inst-123"
                    )
                    assert success is True

