"""Tests for ensure_repository_available function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from application.agents.github.tool_definitions.common.utils.repo_utils import ensure_repository_available


class TestEnsureRepositoryAvailable:
    """Tests for ensure_repository_available function."""

    @pytest.mark.asyncio
    async def test_ensure_repository_available_exists_with_git(self):
        """Test when repository exists with .git directory."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            
            result = await ensure_repository_available("/repo/path")
            
            assert result[0] is True
            assert "available" in result[1].lower()
            assert result[2] == "/repo/path"

    @pytest.mark.asyncio
    async def test_ensure_repository_available_not_exists_no_context(self):
        """Test when repository doesn't exist and no tool context provided."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            
            result = await ensure_repository_available("/repo/path", tool_context=None)
            
            assert result[0] is False
            assert "not available" in result[1].lower()
            assert result[2] == "/repo/path"

    @pytest.mark.asyncio
    async def test_ensure_repository_available_not_require_git(self):
        """Test with require_git=False."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            
            result = await ensure_repository_available("/repo/path", require_git=False)
            
            assert result[0] is True
            assert result[2] == "/repo/path"

    @pytest.mark.asyncio
    async def test_ensure_repository_available_missing_repo_url(self):
        """Test when repository URL is missing from context."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"branch_name": "main"}
        
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            
            result = await ensure_repository_available(
                "/repo/path",
                tool_context=mock_tool_context
            )
            
            assert result[0] is False
            assert "insufficient information" in result[1].lower()

    @pytest.mark.asyncio
    async def test_ensure_repository_available_missing_branch(self):
        """Test when branch name is missing from context."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {"repository_url": "https://github.com/test/repo"}
        
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            
            result = await ensure_repository_available(
                "/repo/path",
                tool_context=mock_tool_context
            )
            
            assert result[0] is False
            assert "insufficient information" in result[1].lower()

    @pytest.mark.asyncio
    async def test_ensure_repository_available_clone_success(self):
        """Test successful repository cloning."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {
            "repository_url": "https://github.com/test/repo",
            "branch_name": "main",
            "installation_id": "123",
            "repository_name": "repo",
            "repository_owner": "test"
        }

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch("application.routes.repository_routes._ensure_repository_cloned") as mock_clone:
                mock_clone.return_value = (True, "Cloned", "/repo/cloned")

                result = await ensure_repository_available(
                    "/repo/path",
                    tool_context=mock_tool_context
                )

                assert result[0] is True
                assert "cloned" in result[1].lower()
                assert result[2] == "/repo/cloned"

    @pytest.mark.asyncio
    async def test_ensure_repository_available_clone_failure(self):
        """Test failed repository cloning."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {
            "repository_url": "https://github.com/test/repo",
            "branch_name": "main"
        }

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch("application.routes.repository_routes._ensure_repository_cloned") as mock_clone:
                mock_clone.return_value = (False, "Clone failed", "/repo/path")

                result = await ensure_repository_available(
                    "/repo/path",
                    tool_context=mock_tool_context
                )

                assert result[0] is False
                assert "failed" in result[1].lower()

    @pytest.mark.asyncio
    async def test_ensure_repository_available_clone_exception(self):
        """Test exception during repository cloning."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {
            "repository_url": "https://github.com/test/repo",
            "branch_name": "main"
        }

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch("application.routes.repository_routes._ensure_repository_cloned") as mock_clone:
                mock_clone.side_effect = Exception("Clone error")

                result = await ensure_repository_available(
                    "/repo/path",
                    tool_context=mock_tool_context
                )

                assert result[0] is False
                assert "exception" in result[1].lower()

    @pytest.mark.asyncio
    async def test_ensure_repository_available_user_repository_url_priority(self):
        """Test that user_repository_url takes priority over repository_url."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {
            "user_repository_url": "https://github.com/user/repo",
            "repository_url": "https://github.com/default/repo",
            "branch_name": "main"
        }

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch("application.routes.repository_routes._ensure_repository_cloned") as mock_clone:
                mock_clone.return_value = (True, "Cloned", "/repo/cloned")

                result = await ensure_repository_available(
                    "/repo/path",
                    tool_context=mock_tool_context
                )

                # Verify user_repository_url was used
                call_args = mock_clone.call_args
                assert call_args[1]["repository_url"] == "https://github.com/user/repo"

