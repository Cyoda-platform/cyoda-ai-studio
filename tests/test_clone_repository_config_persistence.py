"""
Test to verify that clone_repository properly persists repository configuration
including repository_type, which is needed for commit_and_push_changes.

This test ensures that when cloning with use_existing_branch=True,
the repository_type is stored in the tool context so that subsequent
commit_and_push_changes calls can find it.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from application.agents.shared.repository_tools import clone_repository


class TestCloneRepositoryConfigPersistence:
    """Test that clone_repository persists all required configuration."""

    @pytest.fixture
    def temp_repo_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context."""
        context = MagicMock()
        context.state = {
            "conversation_id": "test-conversation-id",
            "repository_type": "public",  # Set by set_repository_config
        }
        return context

    @pytest.mark.asyncio
    async def test_clone_existing_branch_preserves_repository_type(
        self, temp_repo_dir, mock_tool_context
    ):
        """
        Test that when cloning with use_existing_branch=True,
        the repository_type is preserved in the tool context.
        """
        # Create a mock git repository
        repo_path = Path(temp_repo_dir)
        git_dir = repo_path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)

        # Mock the git commands
        with patch(
            "application.agents.shared.repository_tools._run_git_command"
        ) as mock_git:
            # Mock successful git operations
            mock_git.return_value = (0, "success", "")

            # Call clone_repository with existing branch
            result = await clone_repository(
                language="python",
                branch_name="existing-branch",
                target_directory=str(repo_path),
                use_existing_branch=True,
                tool_context=mock_tool_context,
            )

            # Verify success
            assert "SUCCESS" in result
            assert "existing-branch" in result

        # Verify that repository_type is preserved in context
        assert mock_tool_context.state["repository_type"] == "public"
        assert mock_tool_context.state["branch_name"] == "existing-branch"
        assert mock_tool_context.state["language"] == "python"
        assert mock_tool_context.state["repository_path"] == str(repo_path)

    @pytest.mark.asyncio
    async def test_clone_new_branch_stores_repository_type(
        self, temp_repo_dir, mock_tool_context
    ):
        """
        Test that when cloning with use_existing_branch=False,
        the repository_type is stored in the tool context.
        """
        # Create a mock git repository
        repo_path = Path(temp_repo_dir)
        git_dir = repo_path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)

        # Mock the git commands
        with patch(
            "application.agents.shared.repository_tools._run_git_command"
        ) as mock_git:
            # Mock successful git operations
            mock_git.return_value = (0, "success", "")

            # Mock entity service for conversation update
            with patch(
                "application.agents.shared.repository_tools.get_entity_service"
            ) as mock_entity_service:
                mock_service = AsyncMock()
                mock_entity_service.return_value = mock_service
                mock_service.get_by_id.return_value = MagicMock(data={})
                mock_service.update.return_value = None

                # Call clone_repository with new branch
                result = await clone_repository(
                    language="python",
                    branch_name="new-feature-branch",
                    target_directory=str(repo_path),
                    use_existing_branch=False,
                    tool_context=mock_tool_context,
                )

                # Verify success
                assert "SUCCESS" in result

        # Verify that repository_type is stored in context
        assert mock_tool_context.state["repository_type"] == "public"
        assert mock_tool_context.state["branch_name"] == "new-feature-branch"
        assert mock_tool_context.state["language"] == "python"
        assert mock_tool_context.state["repository_path"] == str(repo_path)

    @pytest.mark.asyncio
    async def test_clone_already_exists_preserves_repository_type(
        self, temp_repo_dir, mock_tool_context
    ):
        """
        Test that when repository already exists,
        the repository_type is preserved in the tool context.
        """
        # Create a mock git repository
        repo_path = Path(temp_repo_dir)
        git_dir = repo_path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)

        # Call clone_repository when repo already exists
        result = await clone_repository(
            language="python",
            branch_name="existing-branch",
            target_directory=str(repo_path),
            use_existing_branch=True,
            tool_context=mock_tool_context,
        )

        # Verify success
        assert "SUCCESS" in result
        assert "already exists" in result

        # Verify that repository_type is preserved in context
        assert mock_tool_context.state["repository_type"] == "public"
        assert mock_tool_context.state["branch_name"] == "existing-branch"
        assert mock_tool_context.state["language"] == "python"
        assert mock_tool_context.state["repository_path"] == str(repo_path)

    @pytest.mark.asyncio
    async def test_commit_and_push_can_find_repository_type(
        self, temp_repo_dir, mock_tool_context
    ):
        """
        Test that after clone_repository stores repository_type,
        commit_and_push_changes can find it in the context.
        """
        # Create a mock git repository
        repo_path = Path(temp_repo_dir)
        git_dir = repo_path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)

        # Call clone_repository
        with patch(
            "application.agents.shared.repository_tools._run_git_command"
        ) as mock_git:
            mock_git.return_value = (0, "success", "")

            await clone_repository(
                language="python",
                branch_name="existing-branch",
                target_directory=str(repo_path),
                use_existing_branch=True,
                tool_context=mock_tool_context,
            )

        # Verify that all required fields for commit_and_push_changes are present
        assert mock_tool_context.state.get("repository_path") is not None
        assert mock_tool_context.state.get("branch_name") is not None
        assert mock_tool_context.state.get("language") is not None
        assert mock_tool_context.state.get("repository_type") is not None

        # This is what commit_and_push_changes checks
        repository_type = mock_tool_context.state.get("repository_type")
        assert repository_type is not None, (
            "repository_type must be set for commit_and_push_changes to work"
        )

