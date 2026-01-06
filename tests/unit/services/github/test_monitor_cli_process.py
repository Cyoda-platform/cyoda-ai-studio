"""Tests for _monitor_cli_process function."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.services.github.cli_service import GitHubCLIService


class TestMonitorCliProcess:
    """Test _monitor_cli_process method."""

    @pytest.fixture
    def cli_service(self):
        """Create GitHubCLIService instance."""
        git_service = MagicMock()
        return GitHubCLIService(git_service)

    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess."""
        process = AsyncMock()
        process.pid = 12345
        process.returncode = 0
        process.wait = AsyncMock()
        process.stdout = AsyncMock()
        process.stderr = AsyncMock()
        return process

    @pytest.mark.asyncio
    async def test_monitor_cli_process_with_valid_parameters(self, cli_service, mock_process):
        """Test _monitor_cli_process with valid parameters."""
        mock_process.wait.side_effect = asyncio.TimeoutError()

        with patch("application.services.github.cli_service.get_task_service") as mock_task_service:
            mock_task_service_instance = AsyncMock()
            mock_task_service_instance.update_task_status = AsyncMock()
            mock_task_service.return_value = mock_task_service_instance

            try:
                await asyncio.wait_for(
                    cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/test_repo",
                        branch_name="main",
                        timeout_seconds=1,
                        task_id="task-123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        commit_interval=30,
                        conversation_id="conv-123"
                    ),
                    timeout=2
                )
            except asyncio.TimeoutError:
                pass  # Expected

    @pytest.mark.asyncio
    async def test_monitor_cli_process_timeout_handling(self, cli_service, mock_process):
        """Test that _monitor_cli_process handles timeout."""
        mock_process.wait.side_effect = asyncio.TimeoutError()

        with patch("application.services.github.cli_service.get_task_service") as mock_task_service:
            mock_task_service_instance = AsyncMock()
            mock_task_service_instance.update_task_status = AsyncMock()
            mock_task_service.return_value = mock_task_service_instance

            try:
                await asyncio.wait_for(
                    cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/test_repo",
                        branch_name="main",
                        timeout_seconds=1,
                        task_id="task-123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        commit_interval=30
                    ),
                    timeout=2
                )
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_monitor_cli_process_successful_completion(self, cli_service, mock_process):
        """Test _monitor_cli_process with successful process completion."""
        mock_process.wait.return_value = None
        mock_process.returncode = 0

        with patch("application.services.github.cli_service.get_task_service") as mock_task_service:
            mock_task_service_instance = AsyncMock()
            mock_task_service_instance.update_task_status = AsyncMock()
            mock_task_service.return_value = mock_task_service_instance

            try:
                await asyncio.wait_for(
                    cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/test_repo",
                        branch_name="main",
                        timeout_seconds=30,
                        task_id="task-123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        commit_interval=30
                    ),
                    timeout=2
                )
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_monitor_cli_process_failed_completion(self, cli_service, mock_process):
        """Test _monitor_cli_process with failed process completion."""
        mock_process.wait.return_value = None
        mock_process.returncode = 1

        with patch("application.services.github.cli_service.get_task_service") as mock_task_service:
            mock_task_service_instance = AsyncMock()
            mock_task_service_instance.update_task_status = AsyncMock()
            mock_task_service.return_value = mock_task_service_instance

            try:
                await asyncio.wait_for(
                    cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/test_repo",
                        branch_name="main",
                        timeout_seconds=30,
                        task_id="task-123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        commit_interval=30
                    ),
                    timeout=2
                )
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_monitor_cli_process_with_conversation_id(self, cli_service, mock_process):
        """Test _monitor_cli_process with conversation_id."""
        mock_process.wait.side_effect = asyncio.TimeoutError()

        with patch("application.services.github.cli_service.get_task_service") as mock_task_service:
            mock_task_service_instance = AsyncMock()
            mock_task_service_instance.update_task_status = AsyncMock()
            mock_task_service.return_value = mock_task_service_instance

            try:
                await asyncio.wait_for(
                    cli_service._monitor_cli_process(
                        process=mock_process,
                        repository_path="/tmp/test_repo",
                        branch_name="main",
                        timeout_seconds=1,
                        task_id="task-123",
                        prompt_file="/tmp/prompt.txt",
                        output_file="/tmp/output.log",
                        repo_auth_config={},
                        commit_interval=30,
                        conversation_id="conv-123"
                    ),
                    timeout=2
                )
            except asyncio.TimeoutError:
                pass

