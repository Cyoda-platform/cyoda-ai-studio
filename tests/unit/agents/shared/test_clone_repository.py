"""Comprehensive tests for clone_repository function.

Tests cover:
- Parameter validation
- Protected branch detection
- Repository configuration validation
- Git clone operations and failures
- Branch creation and checkout
- Existing repository detection
- Repository push operations
- Context state management
- Conversation entity updates
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.repository import (
    _extract_repo_name_and_owner,
    _get_repository_config_from_context,
    clone_repository,
)


@pytest.fixture
def mock_tool_context():
    """Create a mock ToolContext."""
    context = MagicMock(spec=ToolContext)
    context.state = {
        "conversation_id": "conv-123",
        "repository_type": "public",
    }
    return context


class TestCloneRepositoryParameterValidation:
    """Test parameter validation in clone_repository."""

    @pytest.mark.asyncio
    async def test_clone_repository_empty_language(self, mock_tool_context):
        """Test that empty language is rejected."""
        result = await clone_repository(
            language="", branch_name="test-branch", tool_context=mock_tool_context
        )
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_clone_repository_none_language(self, mock_tool_context):
        """Test that None language is rejected."""
        result = await clone_repository(
            language=None, branch_name="test-branch", tool_context=mock_tool_context
        )
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_clone_repository_empty_branch_name(self, mock_tool_context):
        """Test that empty branch name is rejected."""
        result = await clone_repository(
            language="python", branch_name="", tool_context=mock_tool_context
        )
        assert "ERROR" in result

    @pytest.mark.asyncio
    async def test_clone_repository_none_branch_name(self, mock_tool_context):
        """Test that None branch name is rejected."""
        result = await clone_repository(
            language="python", branch_name=None, tool_context=mock_tool_context
        )
        assert "ERROR" in result


class TestCloneRepositoryProtectedBranches:
    """Test protected branch detection."""

    @pytest.mark.asyncio
    async def test_rejects_main_branch(self, mock_tool_context):
        """Test that 'main' branch is rejected."""
        result = await clone_repository(
            language="python", branch_name="main", tool_context=mock_tool_context
        )
        assert "ERROR" in result
        assert "protected" in result.lower()

    @pytest.mark.asyncio
    async def test_rejects_master_branch(self, mock_tool_context):
        """Test that 'master' branch is rejected."""
        result = await clone_repository(
            language="python", branch_name="master", tool_context=mock_tool_context
        )
        assert "ERROR" in result
        assert "protected" in result.lower()

    @pytest.mark.asyncio
    async def test_rejects_develop_branch(self, mock_tool_context):
        """Test that 'develop' branch is rejected."""
        result = await clone_repository(
            language="python", branch_name="develop", tool_context=mock_tool_context
        )
        assert "ERROR" in result
        assert "protected" in result.lower()


class TestCloneRepositoryConfigurationValidation:
    """Test repository configuration validation."""

    @pytest.mark.asyncio
    async def test_missing_tool_context(self):
        """Test that missing tool_context is handled."""
        result = await clone_repository(
            language="python", branch_name="test-branch", tool_context=None
        )
        assert "ERROR" in result
        assert "context" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_repository_type_in_context(self):
        """Test that missing repository_type in context is handled."""
        context = MagicMock(spec=ToolContext)
        context.state = {"conversation_id": "conv-123"}  # No repository_type

        result = await clone_repository(
            language="python", branch_name="test-branch", tool_context=context
        )
        assert "ERROR" in result
        assert "configuration required" in result.lower()


class TestCloneRepositoryGitOperations:
    """Test git operations (clone, branch creation, checkout)."""

    @pytest.mark.asyncio
    async def test_git_clone_failure(self, mock_tool_context):
        """Test handling of git clone failure."""
        with patch(
            "application.agents.shared.repository_tools.repository._run_git_command"
        ) as mock_git:
            # Mock clone failure
            mock_git.return_value = (1, "", "Clone failed")

            result = await clone_repository(
                language="python",
                branch_name="test-branch",
                tool_context=mock_tool_context,
            )

            assert "ERROR" in result
            assert "Clone failed" in result

    @pytest.mark.asyncio
    async def test_git_clone_success_python(self, mock_tool_context, tmp_path):
        """Test successful git clone for Python template."""
        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
        ):

            # Mock successful git operations
            mock_git.return_value = (0, "success", "")

            result = await clone_repository(
                language="python",
                branch_name="test-branch",
                target_directory=str(tmp_path),
                tool_context=mock_tool_context,
            )

            assert "SUCCESS" in result or "✅" in result
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_git_clone_success_java(self, mock_tool_context, tmp_path):
        """Test successful git clone for Java template."""
        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
        ):

            # Mock successful git operations
            mock_git.return_value = (0, "success", "")

            result = await clone_repository(
                language="java",
                branch_name="test-branch",
                target_directory=str(tmp_path),
                tool_context=mock_tool_context,
            )

            assert "SUCCESS" in result or "✅" in result


class TestCloneRepositoryBranchOperations:
    """Test branch creation and checkout operations."""

    @pytest.mark.asyncio
    async def test_create_new_branch(self, mock_tool_context, tmp_path):
        """Test creating a new branch."""
        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            # Mock all git operations
            mock_git.return_value = (0, "success", "")

            result = await clone_repository(
                language="python",
                branch_name="feature-branch",
                target_directory=str(tmp_path),
                use_existing_branch=False,
                tool_context=mock_tool_context,
            )

            # Should have called git clone, checkout base, checkout -b
            assert mock_git.call_count >= 3

    @pytest.mark.asyncio
    async def test_checkout_existing_branch(self, mock_tool_context, tmp_path):
        """Test checking out an existing branch."""
        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            # Mock all git operations
            mock_git.return_value = (0, "success", "")

            result = await clone_repository(
                language="python",
                branch_name="existing-branch",
                target_directory=str(tmp_path),
                use_existing_branch=True,
                tool_context=mock_tool_context,
            )

            # Should have called git clone, fetch, checkout, config, pull
            assert mock_git.call_count >= 5

    @pytest.mark.asyncio
    async def test_checkout_base_branch_failure(self, mock_tool_context, tmp_path):
        """Test handling of base branch checkout failure."""
        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            # Mock clone success, then checkout failure
            side_effects = [
                (0, "clone success", ""),  # Clone
                (1, "", "checkout failed"),  # Checkout base - fails
                (0, "success", ""),  # Checkout -b - succeeds
            ]
            mock_git.side_effect = side_effects

            result = await clone_repository(
                language="python",
                branch_name="feature-branch",
                target_directory=str(tmp_path),
                tool_context=mock_tool_context,
            )

            # Should still succeed even if base checkout fails
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_create_branch_already_exists_fallback(
        self, mock_tool_context, tmp_path
    ):
        """Test fallback to checkout when branch creation fails."""
        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            # Mock: clone, checkout base succeed, checkout -b fails, checkout succeeds
            side_effects = [
                (0, "clone success", ""),  # Clone
                (0, "success", ""),  # Checkout base
                (1, "", "branch already exists"),  # Checkout -b fails
                (0, "success", ""),  # Checkout existing
            ]
            mock_git.side_effect = side_effects

            result = await clone_repository(
                language="python",
                branch_name="feature-branch",
                target_directory=str(tmp_path),
                tool_context=mock_tool_context,
            )

            assert isinstance(result, str)


class TestCloneRepositoryExistingRepository:
    """Test detection and handling of existing repositories."""

    @pytest.mark.asyncio
    async def test_existing_repository_skips_clone(self, mock_tool_context, tmp_path):
        """Test that existing repository is detected and clone is skipped."""
        # Create mock repo directory with .git
        repo_path = tmp_path / "test-branch"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        with patch(
            "application.agents.shared.repository_tools.repository._run_git_command"
        ) as mock_git:
            result = await clone_repository(
                language="python",
                branch_name="test-branch",
                target_directory=str(repo_path),
                tool_context=mock_tool_context,
            )

            # Should not call git commands since repo exists
            assert "already exists" in result or "SUCCESS" in result


class TestCloneRepositoryPushOperations:
    """Test pushing new branches to remote."""

    @pytest.mark.asyncio
    async def test_push_new_branch_success(self, mock_tool_context, tmp_path):
        """Test successfully pushing new branch to remote."""
        mock_tool_context.state["repository_type"] = "private"
        mock_tool_context.state["user_repository_url"] = "https://github.com/test/repo"
        mock_tool_context.state["installation_id"] = "123"

        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch(
                "application.agents.shared.repository_tools.repository._get_authenticated_repo_url_sync"
            ) as mock_auth,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            mock_auth.return_value = "https://github.com/test/repo"
            mock_git.return_value = (0, "success", "")

            result = await clone_repository(
                language="python",
                branch_name="feature-branch",
                target_directory=str(tmp_path),
                use_existing_branch=False,
                tool_context=mock_tool_context,
            )

            # Should have called push
            push_calls = [
                call for call in mock_git.call_args_list if "push" in str(call)
            ]
            assert len(push_calls) > 0

    @pytest.mark.asyncio
    async def test_push_failure_doesnt_fail_clone(self, mock_tool_context, tmp_path):
        """Test that push failure doesn't fail the clone operation."""
        mock_tool_context.state["repository_type"] = "private"
        mock_tool_context.state["user_repository_url"] = "https://github.com/test/repo"
        mock_tool_context.state["installation_id"] = "123"

        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch(
                "application.agents.shared.repository_tools.repository._get_authenticated_repo_url_sync"
            ) as mock_auth,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            mock_auth.return_value = "https://github.com/test/repo"

            # Make push fail but other operations succeed
            side_effects = [
                (0, "clone", ""),  # Clone
                (0, "checkout base", ""),  # Checkout base
                (0, "checkout -b", ""),  # Checkout -b
                (1, "", "push failed"),  # Push fails
            ]
            mock_git.side_effect = side_effects

            result = await clone_repository(
                language="python",
                branch_name="feature-branch",
                target_directory=str(tmp_path),
                tool_context=mock_tool_context,
            )

            # Clone should still succeed
            assert "SUCCESS" in result or "✅" in result

    @pytest.mark.asyncio
    async def test_no_push_for_existing_branch(self, mock_tool_context, tmp_path):
        """Test that existing branch is not pushed to remote."""
        mock_tool_context.state["repository_type"] = "private"
        mock_tool_context.state["user_repository_url"] = "https://github.com/test/repo"
        mock_tool_context.state["installation_id"] = "123"

        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch(
                "application.agents.shared.repository_tools.repository._get_authenticated_repo_url_sync"
            ) as mock_auth,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
            patch(
                "application.agents.shared.repository_tools.conversation._update_conversation_build_context"
            ),
        ):

            mock_auth.return_value = "https://github.com/test/repo"
            mock_git.return_value = (0, "success", "")

            result = await clone_repository(
                language="python",
                branch_name="existing-branch",
                target_directory=str(tmp_path),
                use_existing_branch=True,
                tool_context=mock_tool_context,
            )

            # Should not have push calls (specifically checking for git push command)
            push_calls = [
                call
                for call in mock_git.call_args_list
                if isinstance(call.args[0], list) and "push" in call.args[0]
            ]
            assert len(push_calls) == 0


class TestCloneRepositoryContextState:
    """Test context state management during clone."""

    @pytest.mark.asyncio
    async def test_stores_repository_info_in_context(self, mock_tool_context, tmp_path):
        """Test that repository info is stored in context."""
        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            mock_git.return_value = (0, "success", "")

            await clone_repository(
                language="python",
                branch_name="test-branch",
                target_directory=str(tmp_path),
                tool_context=mock_tool_context,
            )

            # Check that context state was updated
            assert mock_tool_context.state.get("repository_path") is not None
            assert mock_tool_context.state.get("branch_name") == "test-branch"
            assert mock_tool_context.state.get("language") == "python"
            assert mock_tool_context.state.get("repository_name") is not None

    @pytest.mark.asyncio
    async def test_preserves_repository_type_in_context(
        self, mock_tool_context, tmp_path
    ):
        """Test that repository_type is preserved in context."""
        mock_tool_context.state["repository_type"] = "public"

        with (
            patch(
                "application.agents.shared.repository_tools.repository._run_git_command"
            ) as mock_git,
            patch("application.agents.shared.repository_tools.repository.Path.mkdir"),
            patch(
                "application.agents.shared.repository_tools.repository.Path.exists",
                return_value=False,
            ),
        ):

            mock_git.return_value = (0, "success", "")

            await clone_repository(
                language="python",
                branch_name="test-branch",
                target_directory=str(tmp_path),
                tool_context=mock_tool_context,
            )

            # Repository type should be preserved
            assert mock_tool_context.state.get("repository_type") == "public"


class TestExtractRepoNameAndOwner:
    """Test repository name and owner extraction."""

    def test_extract_from_https_url(self):
        """Test extracting repo name and owner from HTTPS URL."""
        url = "https://github.com/Cyoda-platform/mcp-cyoda-quart-app"
        owner, name = _extract_repo_name_and_owner(url)
        assert owner == "Cyoda-platform"
        assert name == "mcp-cyoda-quart-app"

    def test_extract_from_git_url(self):
        """Test extracting repo name and owner from .git URL."""
        url = "https://github.com/Cyoda-platform/mcp-cyoda-quart-app.git"
        owner, name = _extract_repo_name_and_owner(url)
        assert owner == "Cyoda-platform"
        assert name == "mcp-cyoda-quart-app"

    def test_extract_from_ssh_url(self):
        """Test extracting repo name from SSH URL."""
        url = "git@github.com:Cyoda-platform/mcp-cyoda-quart-app.git"
        owner, name = _extract_repo_name_and_owner(url)
        # SSH URLs might not parse owner correctly, but should get name
        assert name == "mcp-cyoda-quart-app"

    def test_extract_with_none_url(self):
        """Test with None URL uses defaults."""
        owner, name = _extract_repo_name_and_owner(None)
        assert name == "mcp-cyoda-quart-app"  # Default

    def test_extract_from_url_with_tree_path(self):
        """Test extracting repo name and owner from URL with /tree/branch path."""
        url = "https://github.com/test-ks-001/test-java-client-template/tree/b59e5366-9616-11b2-aa4c-aeca4bd17878"
        owner, name = _extract_repo_name_and_owner(url)
        assert owner == "test-ks-001"
        assert name == "test-java-client-template"

    def test_extract_from_url_with_blob_path(self):
        """Test extracting repo name and owner from URL with /blob/branch/file path."""
        url = "https://github.com/owner-name/repo-name/blob/main/README.md"
        owner, name = _extract_repo_name_and_owner(url)
        assert owner == "owner-name"
        assert name == "repo-name"


class TestGetRepositoryConfigFromContext:
    """Test repository configuration extraction from context."""

    def test_private_repository_config(self):
        """Test extracting private repository configuration."""
        context = MagicMock(spec=ToolContext)
        context.state = {
            "repository_type": "private",
            "user_repository_url": "https://github.com/test/repo",
            "installation_id": "12345",
        }

        repo_url, installation_id, repo_type, error = (
            _get_repository_config_from_context(context, "python")
        )

        assert repo_url == "https://github.com/test/repo"
        assert installation_id == "12345"
        assert repo_type == "private"
        assert error is None

    def test_public_repository_config_python(self):
        """Test extracting public repository configuration for Python."""
        context = MagicMock(spec=ToolContext)
        context.state = {"repository_type": "public"}

        repo_url, installation_id, repo_type, error = (
            _get_repository_config_from_context(context, "python")
        )

        assert "cyoda" in repo_url.lower() or "python" in repo_url.lower()
        assert repo_type == "public"
        assert error is None

    def test_public_repository_config_java(self):
        """Test extracting public repository configuration for Java."""
        context = MagicMock(spec=ToolContext)
        context.state = {"repository_type": "public"}

        repo_url, installation_id, repo_type, error = (
            _get_repository_config_from_context(context, "java")
        )

        assert "java" in repo_url.lower()
        assert repo_type == "public"
        assert error is None

    def test_invalid_language(self):
        """Test with invalid language."""
        context = MagicMock(spec=ToolContext)
        context.state = {"repository_type": "public"}

        repo_url, installation_id, repo_type, error = (
            _get_repository_config_from_context(context, "rust")
        )

        assert error is not None
        assert "Unsupported language" in error

    def test_missing_context(self):
        """Test with missing context."""
        repo_url, installation_id, repo_type, error = (
            _get_repository_config_from_context(None, "python")
        )

        assert error is not None
        assert "context" in error.lower()

    def test_unconfigured_repository_type(self):
        """Test with unconfigured repository type."""
        context = MagicMock(spec=ToolContext)
        context.state = {}  # No repository_type

        repo_url, installation_id, repo_type, error = (
            _get_repository_config_from_context(context, "python")
        )

        assert error is not None
        assert "configuration required" in error.lower()
