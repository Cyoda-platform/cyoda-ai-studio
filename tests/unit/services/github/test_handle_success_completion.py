"""Tests for _handle_success_completion method."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.github.cli_service import GitHubCLIService
from application.services.github.operations_service import GitHubOperationsService


class TestHandleSuccessCompletion:
    """Tests for _handle_success_completion method."""

    @pytest.mark.asyncio
    async def test_handle_success_completion_with_changed_files(self):
        """Test successful completion with changed files."""
        git_service = AsyncMock(spec=GitHubOperationsService)
        cli_service = GitHubCLIService(git_service)
        task_service = AsyncMock()

        # Mock commit and push result
        git_service.commit_and_push = AsyncMock(
            return_value={
                "success": True,
                "changed_files": ["file1.py", "file2.py"],
                "canvas_resources": {"entities": ["User"]},
            }
        )

        await cli_service._handle_success_completion(
            task_id="task-123",
            repository_path="/repo",
            branch_name="feature-branch",
            repo_auth_config={"url": "https://github.com/test/repo"},
            task_service=task_service,
            conversation_id="conv-123",
            repository_name="test-repo",
            repository_owner="test-owner",
        )

        # Verify task was updated with success status
        task_service.update_task_status.assert_called_once()
        call_args = task_service.update_task_status.call_args
        assert call_args[1]["status"] == "completed"
        assert call_args[1]["progress"] == 100

    @pytest.mark.asyncio
    async def test_handle_success_completion_no_changed_files(self):
        """Test successful completion with no changed files."""
        git_service = AsyncMock(spec=GitHubOperationsService)
        cli_service = GitHubCLIService(git_service)
        task_service = AsyncMock()

        # Mock commit and push result with no changes
        git_service.commit_and_push = AsyncMock(
            return_value={"success": True, "changed_files": [], "canvas_resources": {}}
        )

        await cli_service._handle_success_completion(
            task_id="task-123",
            repository_path="/repo",
            branch_name="feature-branch",
            repo_auth_config={"url": "https://github.com/test/repo"},
            task_service=task_service,
            conversation_id="conv-123",
            repository_name="test-repo",
            repository_owner="test-owner",
        )

        # Verify task was updated
        task_service.update_task_status.assert_called_once()
        call_args = task_service.update_task_status.call_args
        assert "No files changed" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_handle_success_completion_commit_timeout(self):
        """Test handling timeout during final commit."""
        git_service = AsyncMock(spec=GitHubOperationsService)
        cli_service = GitHubCLIService(git_service)
        task_service = AsyncMock()

        # Mock timeout error
        git_service.commit_and_push = AsyncMock(side_effect=asyncio.TimeoutError())

        await cli_service._handle_success_completion(
            task_id="task-123",
            repository_path="/repo",
            branch_name="feature-branch",
            repo_auth_config={"url": "https://github.com/test/repo"},
            task_service=task_service,
            conversation_id="conv-123",
            repository_name="test-repo",
            repository_owner="test-owner",
        )

        # Verify task was marked as completed despite timeout
        task_service.update_task_status.assert_called_once()
        call_args = task_service.update_task_status.call_args
        assert call_args[1]["status"] == "completed"
        assert "timed out" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_handle_success_completion_commit_failure(self):
        """Test handling failure during final commit."""
        git_service = AsyncMock(spec=GitHubOperationsService)
        cli_service = GitHubCLIService(git_service)
        task_service = AsyncMock()

        # Mock commit failure
        git_service.commit_and_push = AsyncMock(side_effect=Exception("Commit failed"))

        await cli_service._handle_success_completion(
            task_id="task-123",
            repository_path="/repo",
            branch_name="feature-branch",
            repo_auth_config={"url": "https://github.com/test/repo"},
            task_service=task_service,
            conversation_id="conv-123",
            repository_name="test-repo",
            repository_owner="test-owner",
        )

        # Verify task was marked as completed despite commit failure
        task_service.update_task_status.assert_called_once()
        call_args = task_service.update_task_status.call_args
        assert call_args[1]["status"] == "completed"
        assert "failed" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_handle_success_completion_with_canvas_resources(self):
        """Test completion includes canvas resources in metadata."""
        git_service = AsyncMock(spec=GitHubOperationsService)
        cli_service = GitHubCLIService(git_service)
        task_service = AsyncMock()

        # Mock commit and push with canvas resources
        git_service.commit_and_push = AsyncMock(
            return_value={
                "success": True,
                "changed_files": ["file1.py"],
                "canvas_resources": {
                    "entities": ["User", "Product"],
                    "workflows": ["user_workflow"],
                },
            }
        )

        await cli_service._handle_success_completion(
            task_id="task-123",
            repository_path="/repo",
            branch_name="feature-branch",
            repo_auth_config={"url": "https://github.com/test/repo"},
            task_service=task_service,
            conversation_id="conv-123",
            repository_name="test-repo",
            repository_owner="test-owner",
        )

        # Verify metadata includes hook data
        task_service.update_task_status.assert_called_once()
        call_args = task_service.update_task_status.call_args
        metadata = call_args[1]["metadata"]
        assert "hook_data" in metadata
        assert metadata["hook_data"]["resources"] == {
            "entities": ["User", "Product"],
            "workflows": ["user_workflow"],
        }

    @pytest.mark.asyncio
    async def test_handle_success_completion_without_conversation_id(self):
        """Test completion without conversation ID doesn't include hook data."""
        git_service = AsyncMock(spec=GitHubOperationsService)
        cli_service = GitHubCLIService(git_service)
        task_service = AsyncMock()

        # Mock commit and push
        git_service.commit_and_push = AsyncMock(
            return_value={
                "success": True,
                "changed_files": ["file1.py"],
                "canvas_resources": {"entities": ["User"]},
            }
        )

        await cli_service._handle_success_completion(
            task_id="task-123",
            repository_path="/repo",
            branch_name="feature-branch",
            repo_auth_config={"url": "https://github.com/test/repo"},
            task_service=task_service,
            conversation_id=None,
            repository_name="test-repo",
            repository_owner="test-owner",
        )

        # Verify metadata doesn't include hook data
        task_service.update_task_status.assert_called_once()
        call_args = task_service.update_task_status.call_args
        metadata = call_args[1]["metadata"]
        assert "hook_data" not in metadata
