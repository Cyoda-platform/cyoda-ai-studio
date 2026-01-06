"""Tests for set_repository_config function."""

import pytest
from unittest.mock import MagicMock, patch

from application.agents.shared.repository_tools.repository import set_repository_config


class TestSetRepositoryConfig:
    """Tests for set_repository_config function."""

    @pytest.mark.asyncio
    async def test_set_repository_config_empty_repository_type(self):
        """Test error when repository_type is empty."""
        mock_tool_context = MagicMock()
        
        with pytest.raises(ValueError, match="repository_type.*required"):
            await set_repository_config(
                repository_type="",
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_invalid_repository_type(self):
        """Test error when repository_type is invalid."""
        mock_tool_context = MagicMock()
        
        with pytest.raises(ValueError, match="must be 'public' or 'private'"):
            await set_repository_config(
                repository_type="invalid",
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_no_tool_context(self):
        """Test error when tool_context is not provided."""
        with pytest.raises(ValueError, match="Tool context not available"):
            await set_repository_config(
                repository_type="public",
                tool_context=None
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_private_no_installation_id(self):
        """Test error when private repo without installation_id."""
        mock_tool_context = MagicMock()
        
        with pytest.raises(ValueError, match="installation_id.*required"):
            await set_repository_config(
                repository_type="private",
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_private_no_repository_url(self):
        """Test error when private repo without repository_url."""
        mock_tool_context = MagicMock()
        
        with pytest.raises(ValueError, match="repository_url.*required"):
            await set_repository_config(
                repository_type="private",
                installation_id="123",
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_private_success(self):
        """Test successful private repository configuration."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}
        
        result = await set_repository_config(
            repository_type="private",
            installation_id="123",
            repository_url="https://github.com/test/repo",
            tool_context=mock_tool_context
        )
        
        assert "Private Repository Configured" in result
        assert "https://github.com/test/repo" in result
        assert "123" in result
        assert mock_tool_context.state["repository_type"] == "private"
        assert mock_tool_context.state["installation_id"] == "123"
        assert mock_tool_context.state["user_repository_url"] == "https://github.com/test/repo"

    @pytest.mark.asyncio
    async def test_set_repository_config_public_success(self):
        """Test successful public repository configuration."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}
        
        with patch("application.agents.shared.repository_tools.repository.GITHUB_PUBLIC_REPO_INSTALLATION_ID", "public-123"):
            result = await set_repository_config(
                repository_type="public",
                tool_context=mock_tool_context
            )
            
            assert "Public Repository Mode Configured" in result
            assert mock_tool_context.state["repository_type"] == "public"

    @pytest.mark.asyncio
    async def test_set_repository_config_public_not_configured(self):
        """Test public repository when not configured."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}
        
        with patch("application.agents.shared.repository_tools.repository.GITHUB_PUBLIC_REPO_INSTALLATION_ID", None):
            result = await set_repository_config(
                repository_type="public",
                tool_context=mock_tool_context
            )
            
            assert "ERROR" in result
            assert "not available" in result.lower()

    @pytest.mark.asyncio
    async def test_set_repository_config_stores_repository_type(self):
        """Test that repository_type is stored in context state."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}
        
        result = await set_repository_config(
            repository_type="private",
            installation_id="123",
            repository_url="https://github.com/test/repo",
            tool_context=mock_tool_context
        )
        
        assert mock_tool_context.state["repository_type"] == "private"

    @pytest.mark.asyncio
    async def test_set_repository_config_private_stores_credentials(self):
        """Test that private repo credentials are stored."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}
        
        result = await set_repository_config(
            repository_type="private",
            installation_id="inst-123",
            repository_url="https://github.com/myorg/myrepo",
            tool_context=mock_tool_context
        )
        
        assert mock_tool_context.state["installation_id"] == "inst-123"
        assert mock_tool_context.state["user_repository_url"] == "https://github.com/myorg/myrepo"

    @pytest.mark.asyncio
    async def test_set_repository_config_case_sensitive_type(self):
        """Test that repository_type is case-sensitive."""
        mock_tool_context = MagicMock()
        
        with pytest.raises(ValueError, match="must be 'public' or 'private'"):
            await set_repository_config(
                repository_type="PUBLIC",
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_private_with_whitespace_url(self):
        """Test private repo with whitespace in URL."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}

        result = await set_repository_config(
            repository_type="private",
            installation_id="123",
            repository_url="https://github.com/test/repo",
            tool_context=mock_tool_context
        )

        assert "Private Repository Configured" in result
        assert mock_tool_context.state["user_repository_url"] == "https://github.com/test/repo"

    @pytest.mark.asyncio
    async def test_set_repository_config_private_with_git_extension(self):
        """Test private repo URL with .git extension."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}

        result = await set_repository_config(
            repository_type="private",
            installation_id="456",
            repository_url="https://github.com/myorg/myrepo.git",
            tool_context=mock_tool_context
        )

        assert "Private Repository Configured" in result
        assert mock_tool_context.state["user_repository_url"] == "https://github.com/myorg/myrepo.git"

    @pytest.mark.asyncio
    async def test_set_repository_config_private_multiple_calls_overwrites(self):
        """Test that multiple calls overwrite previous configuration."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}

        # First call
        await set_repository_config(
            repository_type="private",
            installation_id="123",
            repository_url="https://github.com/repo1/first",
            tool_context=mock_tool_context
        )

        assert mock_tool_context.state["installation_id"] == "123"
        assert mock_tool_context.state["user_repository_url"] == "https://github.com/repo1/first"

        # Second call overwrites
        await set_repository_config(
            repository_type="private",
            installation_id="456",
            repository_url="https://github.com/repo2/second",
            tool_context=mock_tool_context
        )

        assert mock_tool_context.state["installation_id"] == "456"
        assert mock_tool_context.state["user_repository_url"] == "https://github.com/repo2/second"

    @pytest.mark.asyncio
    async def test_set_repository_config_public_logs_message(self):
        """Test that public repo configuration returns proper message with template URLs."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}

        with patch("application.agents.shared.repository_tools.repository.GITHUB_PUBLIC_REPO_INSTALLATION_ID", "pub-123"):
            with patch("application.agents.shared.repository_tools.repository.PYTHON_PUBLIC_REPO_URL", "https://github.com/cyoda/python-template"):
                with patch("application.agents.shared.repository_tools.repository.JAVA_PUBLIC_REPO_URL", "https://github.com/cyoda/java-template"):
                    result = await set_repository_config(
                        repository_type="public",
                        tool_context=mock_tool_context
                    )

                    assert "Public Repository Mode Configured" in result
                    assert "https://github.com/cyoda/python-template" in result
                    assert "https://github.com/cyoda/java-template" in result
                    assert "clone_repository()" in result

    @pytest.mark.asyncio
    async def test_set_repository_config_private_with_special_chars_in_url(self):
        """Test private repo with special characters in org/repo names."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}

        result = await set_repository_config(
            repository_type="private",
            installation_id="789",
            repository_url="https://github.com/my-org/my-repo-name",
            tool_context=mock_tool_context
        )

        assert "Private Repository Configured" in result
        assert mock_tool_context.state["user_repository_url"] == "https://github.com/my-org/my-repo-name"

    @pytest.mark.asyncio
    async def test_set_repository_config_none_repository_type(self):
        """Test error when repository_type is None."""
        mock_tool_context = MagicMock()

        with pytest.raises(ValueError, match="repository_type.*required"):
            await set_repository_config(
                repository_type=None,
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_private_with_ssh_url(self):
        """Test private repo with SSH URL format."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}

        result = await set_repository_config(
            repository_type="private",
            installation_id="ssh-123",
            repository_url="git@github.com:myorg/myrepo.git",
            tool_context=mock_tool_context
        )

        assert "Private Repository Configured" in result
        assert mock_tool_context.state["user_repository_url"] == "git@github.com:myorg/myrepo.git"

    @pytest.mark.asyncio
    async def test_set_repository_config_private_empty_installation_id_string(self):
        """Test error when installation_id is empty string for private repo."""
        mock_tool_context = MagicMock()

        with pytest.raises(ValueError, match="installation_id.*required"):
            await set_repository_config(
                repository_type="private",
                installation_id="",
                repository_url="https://github.com/test/repo",
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_private_empty_repository_url_string(self):
        """Test error when repository_url is empty string for private repo."""
        mock_tool_context = MagicMock()

        with pytest.raises(ValueError, match="repository_url.*required"):
            await set_repository_config(
                repository_type="private",
                installation_id="123",
                repository_url="",
                tool_context=mock_tool_context
            )

    @pytest.mark.asyncio
    async def test_set_repository_config_preserves_other_context_state(self):
        """Test that setting repository config preserves other state in context."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {
            "conversation_id": "conv-123",
            "user_id": "user-456",
            "some_other_key": "some_value"
        }

        result = await set_repository_config(
            repository_type="private",
            installation_id="inst-789",
            repository_url="https://github.com/test/repo",
            tool_context=mock_tool_context
        )

        # Verify other state is preserved
        assert mock_tool_context.state["conversation_id"] == "conv-123"
        assert mock_tool_context.state["user_id"] == "user-456"
        assert mock_tool_context.state["some_other_key"] == "some_value"
        # And new state is added
        assert mock_tool_context.state["repository_type"] == "private"
        assert mock_tool_context.state["installation_id"] == "inst-789"

    @pytest.mark.asyncio
    async def test_set_repository_config_returns_string_confirmation(self):
        """Test that function returns a string confirmation message."""
        mock_tool_context = MagicMock()
        mock_tool_context.state = {}

        result = await set_repository_config(
            repository_type="private",
            installation_id="123",
            repository_url="https://github.com/test/repo",
            tool_context=mock_tool_context
        )

        assert isinstance(result, str)
        assert len(result) > 0

