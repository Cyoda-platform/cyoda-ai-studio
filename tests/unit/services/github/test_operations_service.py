"""Tests for GitHubOperationsService.ensure_repository function."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from application.services.github.operations_service import GitHubOperationsService


class TestEnsureRepository:
    """Test GitHubOperationsService.ensure_repository function."""

    @pytest.mark.asyncio
    async def test_ensure_repository_already_exists(self):
        """Test function returns success when repository already exists."""
        service = GitHubOperationsService()
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.mkdir"):
                success, message, path = await service.ensure_repository(
                    repository_url="https://github.com/test/repo",
                    repository_branch="main",
                    repository_name="repo"
                )
                assert success is True
                assert path is not None

    @pytest.mark.asyncio
    async def test_ensure_repository_extract_name_from_url(self):
        """Test function extracts repository name from URL."""
        service = GitHubOperationsService()

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                # Patch run_subprocess where it's used in repository_operations
                with patch("application.services.github.operations_service.service.repository_operations.run_subprocess") as mock_run:
                    mock_result = {"returncode": 0, "stdout": "", "stderr": ""}
                    mock_run.return_value = mock_result

                    success, message, path = await service.ensure_repository(
                        repository_url="https://github.com/test/my-repo",
                        repository_branch="main"
                    )
                    # Should extract "my-repo" from URL
                    assert mock_run.called

    @pytest.mark.asyncio
    async def test_ensure_repository_invalid_url(self):
        """Test function returns error for invalid URL."""
        service = GitHubOperationsService()
        
        success, message, path = await service.ensure_repository(
            repository_url="invalid-url",
            repository_branch="main"
        )
        assert success is False
        assert "Could not extract" in message

    @pytest.mark.asyncio
    async def test_ensure_repository_clone_failure(self):
        """Test function returns error when clone fails."""
        service = GitHubOperationsService()

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("application.services.github.operations_service.service.repository_operations.run_subprocess") as mock_run:
                    mock_result = {"returncode": 1, "stdout": "", "stderr": "Clone failed"}
                    mock_run.return_value = mock_result

                    success, message, path = await service.ensure_repository(
                        repository_url="https://github.com/test/repo",
                        repository_branch="main",
                        repository_name="repo"
                    )
                    assert success is False
                    assert "Failed to clone" in message

    @pytest.mark.asyncio
    async def test_ensure_repository_with_installation_id(self):
        """Test function uses installation ID for authentication."""
        service = GitHubOperationsService()

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("application.services.github.operations_service.service.repository_operations.run_subprocess") as mock_run:
                    mock_result = {"returncode": 0, "stdout": "", "stderr": ""}
                    mock_run.return_value = mock_result

                    with patch("application.services.github.operations_service.InstallationTokenManager") as mock_token_mgr:
                        mock_mgr_instance = AsyncMock()
                        mock_mgr_instance.get_installation_token = AsyncMock(return_value="test-token")
                        mock_token_mgr.return_value = mock_mgr_instance

                        success, message, path = await service.ensure_repository(
                            repository_url="https://github.com/test/repo",
                            repository_branch="main",
                            repository_name="repo",
                            installation_id="123"
                        )
                        assert success is True

    @pytest.mark.asyncio
    async def test_ensure_repository_timeout(self):
        """Test function handles timeout gracefully."""
        service = GitHubOperationsService()

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("application.services.github.operations_service.service.repository_operations.run_subprocess") as mock_run:
                    mock_run.side_effect = asyncio.TimeoutError()

                    success, message, path = await service.ensure_repository(
                        repository_url="https://github.com/test/repo",
                        repository_branch="main",
                        repository_name="repo"
                    )
                    assert success is False
                    assert "error cloning repository" in message.lower()

    @pytest.mark.asyncio
    async def test_ensure_repository_exception_handling(self):
        """Test function handles exceptions gracefully."""
        service = GitHubOperationsService()
        
        with patch("pathlib.Path.exists", side_effect=Exception("Path error")):
            success, message, path = await service.ensure_repository(
                repository_url="https://github.com/test/repo",
                repository_branch="main",
                repository_name="repo"
            )
            assert success is False
            assert "Error" in message

