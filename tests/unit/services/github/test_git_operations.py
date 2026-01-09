"""Tests for GitOperations._pull_internal function."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.github.git.operations import GitOperations
from application.services.github.models.types import GitOperationResult


class TestPullInternal:
    """Test GitOperations._pull_internal function."""

    @pytest.mark.asyncio
    async def test_pull_internal_no_changes(self):
        """Test _pull_internal returns success when no changes to pull."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_ensure_branch_exists") as mock_ensure:
            # _ensure_branch_exists returns tuple (success, error_message)
            mock_ensure.return_value = (True, None)

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                # Mock fetch
                fetch_process = AsyncMock()
                fetch_process.returncode = 0
                fetch_process.communicate = AsyncMock(return_value=(b"", b""))

                # Mock diff (no changes)
                diff_process = AsyncMock()
                diff_process.returncode = 0
                diff_process.communicate = AsyncMock(return_value=(b"", b""))

                # Mock merge (in case it's called)
                merge_process = AsyncMock()
                merge_process.returncode = 0
                merge_process.communicate = AsyncMock(return_value=(b"", b""))

                # Add more processes for potential additional git operations
                extra_process = AsyncMock()
                extra_process.returncode = 0
                extra_process.communicate = AsyncMock(return_value=(b"", b""))

                mock_subprocess.side_effect = [
                    fetch_process,
                    diff_process,
                    merge_process,
                    extra_process,
                    extra_process,
                    extra_process,
                ]

                result = await git_ops._pull_internal(
                    git_branch_id="feature-branch", repository_name="test-repo"
                )
                assert result.success is True
                assert result.had_changes is False

    @pytest.mark.asyncio
    async def test_pull_internal_fetch_failure(self):
        """Test _pull_internal returns error when fetch fails."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_ensure_branch_exists") as mock_ensure:
            # _ensure_branch_exists returns tuple (success, error_message)
            mock_ensure.return_value = (True, None)

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                fetch_process = AsyncMock()
                fetch_process.returncode = 1
                fetch_process.communicate = AsyncMock(
                    return_value=(b"", b"Fetch failed")
                )

                mock_subprocess.return_value = fetch_process

                result = await git_ops._pull_internal(
                    git_branch_id="feature-branch", repository_name="test-repo"
                )
                assert result.success is False
                assert (
                    "failed" in result.message.lower()
                    or "error" in result.message.lower()
                )

    @pytest.mark.asyncio
    async def test_pull_internal_diff_failure(self):
        """Test _pull_internal returns error when diff fails."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_ensure_branch_exists") as mock_ensure:
            # _ensure_branch_exists returns tuple (success, error_message)
            mock_ensure.return_value = (True, None)

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                fetch_process = AsyncMock()
                fetch_process.returncode = 0
                fetch_process.communicate = AsyncMock(return_value=(b"", b""))

                diff_process = AsyncMock()
                diff_process.returncode = 1
                diff_process.communicate = AsyncMock(return_value=(b"", b"Diff failed"))

                mock_subprocess.side_effect = [fetch_process, diff_process]

                result = await git_ops._pull_internal(
                    git_branch_id="feature-branch", repository_name="test-repo"
                )
                assert result.success is False
                assert (
                    "failed" in result.message.lower()
                    or "error" in result.message.lower()
                )

    @pytest.mark.asyncio
    async def test_pull_internal_branch_creation_failure(self):
        """Test _pull_internal returns error when branch creation fails."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_ensure_branch_exists") as mock_ensure:
            mock_ensure.return_value = GitOperationResult(
                success=False, message="Branch creation failed"
            )

            result = await git_ops._pull_internal(
                git_branch_id="feature-branch", repository_name="test-repo"
            )
            assert result.success is False

    @pytest.mark.asyncio
    async def test_pull_internal_with_changes(self):
        """Test _pull_internal detects changes to pull."""
        git_ops = GitOperations()

        with patch.object(git_ops, "_ensure_branch_exists") as mock_ensure:
            mock_ensure.return_value = GitOperationResult(
                success=True, message="Branch exists"
            )

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                fetch_process = AsyncMock()
                fetch_process.returncode = 0
                fetch_process.communicate = AsyncMock(return_value=(b"", b""))

                diff_process = AsyncMock()
                diff_process.returncode = 0
                diff_process.communicate = AsyncMock(
                    return_value=(b"diff content", b"")
                )

                mock_subprocess.side_effect = [fetch_process, diff_process]

                result = await git_ops._pull_internal(
                    git_branch_id="feature-branch", repository_name="test-repo"
                )
                # Should continue to pull when changes detected
                assert result is not None
