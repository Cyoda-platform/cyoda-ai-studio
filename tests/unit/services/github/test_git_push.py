"""Tests for GitOperations.push function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.github.git.operations import GitOperations
from application.services.github.models.types import GitOperationResult


class TestGitPush:
    """Test GitOperations.push function."""

    @pytest.mark.asyncio
    async def test_push_success(self):
        """Test successful push operation."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_pull_internal") as mock_pull:
            mock_pull.return_value = GitOperationResult(
                success=True, message="Pull successful"
            )

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                # Mock add process
                add_process = AsyncMock()
                add_process.returncode = 0
                add_process.communicate = AsyncMock(return_value=(b"", b""))

                # Mock status process
                status_process = AsyncMock()
                status_process.returncode = 0
                status_process.communicate = AsyncMock(
                    return_value=(b"M file.txt", b"")
                )

                # Mock commit process
                commit_process = AsyncMock()
                commit_process.returncode = 0
                commit_process.communicate = AsyncMock(
                    return_value=(b"[main 123] commit", b"")
                )

                # Mock push process
                push_process = AsyncMock()
                push_process.returncode = 0
                push_process.communicate = AsyncMock(return_value=(b"", b""))

                mock_subprocess.side_effect = [
                    add_process,
                    status_process,
                    commit_process,
                    push_process,
                ]

                result = await git_ops.push(
                    git_branch_id="feature-branch",
                    repository_name="test-repo",
                    file_paths=["file.txt"],
                    commit_message="Add file",
                )
                assert result.success is True

    @pytest.mark.asyncio
    async def test_push_add_failure(self):
        """Test push fails when git add fails."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_pull_internal") as mock_pull:
            mock_pull.return_value = GitOperationResult(
                success=True, message="Pull successful"
            )

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                add_process = AsyncMock()
                add_process.returncode = 1
                add_process.communicate = AsyncMock(return_value=(b"", b"Add failed"))

                mock_subprocess.return_value = add_process

                result = await git_ops.push(
                    git_branch_id="feature-branch",
                    repository_name="test-repo",
                    file_paths=["file.txt"],
                    commit_message="Add file",
                )
                assert result.success is False
                assert "Add failed" in result.message

    @pytest.mark.asyncio
    async def test_push_commit_failure(self):
        """Test push fails when git commit fails."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_pull_internal") as mock_pull:
            mock_pull.return_value = GitOperationResult(
                success=True, message="Pull successful"
            )

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                add_process = AsyncMock()
                add_process.returncode = 0
                add_process.communicate = AsyncMock(return_value=(b"", b""))

                status_process = AsyncMock()
                status_process.returncode = 0
                status_process.communicate = AsyncMock(
                    return_value=(b"M file.txt", b"")
                )

                commit_process = AsyncMock()
                commit_process.returncode = 1
                commit_process.communicate = AsyncMock(
                    return_value=(b"", b"Commit failed")
                )

                mock_subprocess.side_effect = [
                    add_process,
                    status_process,
                    commit_process,
                ]

                result = await git_ops.push(
                    git_branch_id="feature-branch",
                    repository_name="test-repo",
                    file_paths=["file.txt"],
                    commit_message="Add file",
                )
                assert result.success is False

    @pytest.mark.asyncio
    async def test_push_nothing_to_commit(self):
        """Test push succeeds when there's nothing to commit."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_pull_internal") as mock_pull:
            mock_pull.return_value = GitOperationResult(
                success=True, message="Pull successful"
            )

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                add_process = AsyncMock()
                add_process.returncode = 0
                add_process.communicate = AsyncMock(return_value=(b"", b""))

                status_process = AsyncMock()
                status_process.returncode = 0
                status_process.communicate = AsyncMock(return_value=(b"", b""))

                commit_process = AsyncMock()
                commit_process.returncode = 1
                commit_process.communicate = AsyncMock(
                    return_value=(b"nothing to commit", b"")
                )

                mock_subprocess.side_effect = [
                    add_process,
                    status_process,
                    commit_process,
                ]

                result = await git_ops.push(
                    git_branch_id="feature-branch",
                    repository_name="test-repo",
                    file_paths=["file.txt"],
                    commit_message="Add file",
                )
                assert result.success is True
                assert "No changes" in result.message

    @pytest.mark.asyncio
    async def test_push_failure(self):
        """Test push fails when git push fails."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_pull_internal") as mock_pull:
            mock_pull.return_value = GitOperationResult(
                success=True, message="Pull successful"
            )

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                add_process = AsyncMock()
                add_process.returncode = 0
                add_process.communicate = AsyncMock(return_value=(b"", b""))

                status_process = AsyncMock()
                status_process.returncode = 0
                status_process.communicate = AsyncMock(
                    return_value=(b"M file.txt", b"")
                )

                commit_process = AsyncMock()
                commit_process.returncode = 0
                commit_process.communicate = AsyncMock(
                    return_value=(b"[main 123] commit", b"")
                )

                push_process = AsyncMock()
                push_process.returncode = 1
                push_process.communicate = AsyncMock(return_value=(b"", b"Push failed"))

                mock_subprocess.side_effect = [
                    add_process,
                    status_process,
                    commit_process,
                    push_process,
                ]

                result = await git_ops.push(
                    git_branch_id="feature-branch",
                    repository_name="test-repo",
                    file_paths=["file.txt"],
                    commit_message="Add file",
                )
                assert result.success is False
                assert "Push failed" in result.message
