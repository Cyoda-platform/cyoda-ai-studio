"""Tests for _ensure_branch_exists method in GitOperations."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.services.github.git.operations import GitOperations, GitOperationResult


class TestEnsureBranchExists:
    """Tests for _ensure_branch_exists method."""

    @pytest.mark.asyncio
    async def test_ensure_branch_exists_branch_already_exists(self):
        """Test when branch already exists locally."""
        git_ops = GitOperations()

        # Mock subprocess for branch check (returns 0 = exists)
        mock_check_process = AsyncMock()
        mock_check_process.returncode = 0
        mock_check_process.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for checkout
        mock_checkout_process = AsyncMock()
        mock_checkout_process.returncode = 0
        mock_checkout_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = [mock_check_process, mock_checkout_process]

            success, message = await git_ops._ensure_branch_exists(
                clone_dir="/repo",
                git_branch_id="feature-branch"
            )

            assert success is True
            assert message is None or "Checked out" in (message or "")

    @pytest.mark.asyncio
    async def test_ensure_branch_exists_checkout_fails(self):
        """Test when checkout of existing branch fails."""
        git_ops = GitOperations()

        # Mock subprocess for branch check (returns 0 = exists)
        mock_check_process = AsyncMock()
        mock_check_process.returncode = 0
        mock_check_process.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for checkout (fails)
        mock_checkout_process = AsyncMock()
        mock_checkout_process.returncode = 1
        mock_checkout_process.communicate = AsyncMock(return_value=(b"", b"Error message"))

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = [mock_check_process, mock_checkout_process]

            success, message = await git_ops._ensure_branch_exists(
                clone_dir="/repo",
                git_branch_id="feature-branch"
            )

            assert success is False
            assert message and "error" in message.lower()

    @pytest.mark.asyncio
    async def test_ensure_branch_exists_create_new_branch(self):
        """Test creating a new branch when it doesn't exist."""
        git_ops = GitOperations()

        # Mock subprocess for branch check (returns 1 = doesn't exist)
        mock_check_process = AsyncMock()
        mock_check_process.returncode = 1
        mock_check_process.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for base checkout
        mock_base_checkout = AsyncMock()
        mock_base_checkout.returncode = 0
        mock_base_checkout.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for create branch
        mock_create_branch = AsyncMock()
        mock_create_branch.returncode = 0
        mock_create_branch.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for set upstream
        mock_upstream = AsyncMock()
        mock_upstream.returncode = 0
        mock_upstream.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = [
                mock_check_process,
                mock_base_checkout,
                mock_create_branch,
                mock_upstream
            ]

            with patch("os.chdir"):
                with patch("os.getcwd", return_value="/original"):
                    success, message = await git_ops._ensure_branch_exists(
                        clone_dir="/repo",
                        git_branch_id="feature-branch"
                    )

                    assert success is True
                    assert message is None or "Created" in (message or "") or "created" in (message or "").lower()

    @pytest.mark.asyncio
    async def test_ensure_branch_exists_base_checkout_fails(self):
        """Test when base branch checkout fails."""
        git_ops = GitOperations()

        # Mock subprocess for branch check (returns 1 = doesn't exist)
        mock_check_process = AsyncMock()
        mock_check_process.returncode = 1
        mock_check_process.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for base checkout (fails)
        mock_base_checkout = AsyncMock()
        mock_base_checkout.returncode = 1
        mock_base_checkout.communicate = AsyncMock(return_value=(b"", b"Base checkout error"))

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = [mock_check_process, mock_base_checkout]

            success, message = await git_ops._ensure_branch_exists(
                clone_dir="/repo",
                git_branch_id="feature-branch"
            )

            assert success is False
            assert message and "error" in message.lower()

    @pytest.mark.asyncio
    async def test_ensure_branch_exists_create_branch_fails(self):
        """Test when creating new branch fails."""
        git_ops = GitOperations()

        # Mock subprocess for branch check (returns 1 = doesn't exist)
        mock_check_process = AsyncMock()
        mock_check_process.returncode = 1
        mock_check_process.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for base checkout
        mock_base_checkout = AsyncMock()
        mock_base_checkout.returncode = 0
        mock_base_checkout.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for create branch (fails)
        mock_create_branch = AsyncMock()
        mock_create_branch.returncode = 1
        mock_create_branch.communicate = AsyncMock(return_value=(b"", b"Create branch error"))

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = [
                mock_check_process,
                mock_base_checkout,
                mock_create_branch
            ]

            success, message = await git_ops._ensure_branch_exists(
                clone_dir="/repo",
                git_branch_id="feature-branch"
            )

            assert success is False
            assert message and "error" in message.lower()

    @pytest.mark.asyncio
    async def test_ensure_branch_exists_with_custom_base_branch(self):
        """Test creating branch (without custom base branch - not supported)."""
        git_ops = GitOperations()

        # Mock subprocess for branch check (returns 1 = doesn't exist)
        mock_check_process = AsyncMock()
        mock_check_process.returncode = 1
        mock_check_process.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for base checkout
        mock_base_checkout = AsyncMock()
        mock_base_checkout.returncode = 0
        mock_base_checkout.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for create branch
        mock_create_branch = AsyncMock()
        mock_create_branch.returncode = 0
        mock_create_branch.communicate = AsyncMock(return_value=(b"", b""))

        # Mock subprocess for set upstream
        mock_upstream = AsyncMock()
        mock_upstream.returncode = 0
        mock_upstream.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = [
                mock_check_process,
                mock_base_checkout,
                mock_create_branch,
                mock_upstream
            ]

            with patch("os.chdir"):
                with patch("os.getcwd", return_value="/original"):
                    success, message = await git_ops._ensure_branch_exists(
                        clone_dir="/repo",
                        git_branch_id="feature-branch"
                    )

                    assert success is True

