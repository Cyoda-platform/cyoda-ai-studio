"""Unit tests for shared CLI process initialization logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from application.agents.shared.repository_tools.cli_process import (
    start_cli_process,
    setup_and_monitor_cli_process,
)


@pytest.mark.asyncio
async def test_start_cli_process_success():
    """Test successful CLI process startup."""
    mock_process = AsyncMock()
    mock_process.pid = 12345

    with patch("application.agents.shared.repository_tools.cli_process.asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("application.agents.shared.repository_tools.cli_process.get_process_manager") as mock_pm:
            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=True)
            mock_pm_instance.register_process = AsyncMock(return_value=True)
            mock_pm.return_value = mock_pm_instance

            success, error_msg, process = await start_cli_process(
                command=["bash", "script.sh", "arg1"],
                repository_path="/tmp/repo",
                process_type="test",
            )

            assert success is True
            assert error_msg == ""
            assert process == mock_process
            mock_pm_instance.can_start_process.assert_called_once()
            mock_pm_instance.register_process.assert_called_once_with(12345)


@pytest.mark.asyncio
async def test_start_cli_process_process_limit_exceeded():
    """Test CLI process startup when process limit is exceeded."""
    with patch("application.agents.shared.repository_tools.cli_process.get_process_manager") as mock_pm:
        mock_pm_instance = AsyncMock()
        mock_pm_instance.can_start_process = AsyncMock(return_value=False)
        mock_pm_instance.get_active_count = AsyncMock(return_value=5)
        mock_pm.return_value = mock_pm_instance

        success, error_msg, process = await start_cli_process(
            command=["bash", "script.sh"],
            repository_path="/tmp/repo",
            process_type="test",
        )

        assert success is False
        assert "maximum concurrent processes" in error_msg
        assert "(5)" in error_msg
        assert process is None


@pytest.mark.asyncio
async def test_start_cli_process_subprocess_creation_fails():
    """Test CLI process startup when subprocess creation fails."""
    with patch("application.agents.shared.repository_tools.cli_process.asyncio.create_subprocess_exec") as mock_exec:
        mock_exec.side_effect = OSError("Failed to create subprocess")

        with patch("application.agents.shared.repository_tools.cli_process.get_process_manager") as mock_pm:
            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=True)
            mock_pm.return_value = mock_pm_instance

            success, error_msg, process = await start_cli_process(
                command=["bash", "script.sh"],
                repository_path="/tmp/repo",
                process_type="test",
            )

            assert success is False
            assert "Failed to start test process" in error_msg
            assert process is None


@pytest.mark.asyncio
async def test_start_cli_process_registration_fails():
    """Test CLI process startup when process registration fails."""
    mock_process = AsyncMock()
    mock_process.pid = 12345

    with patch("application.agents.shared.repository_tools.cli_process.asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("application.agents.shared.repository_tools.cli_process.get_process_manager") as mock_pm:
            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=True)
            mock_pm_instance.register_process = AsyncMock(return_value=False)
            mock_pm.return_value = mock_pm_instance

            with patch("application.agents.shared.repository_tools.cli_process._terminate_process") as mock_terminate:
                success, error_msg, process = await start_cli_process(
                    command=["bash", "script.sh"],
                    repository_path="/tmp/repo",
                    process_type="test",
                )

                assert success is False
                assert "process limit exceeded" in error_msg
                assert process is None
                mock_terminate.assert_called_once_with(mock_process)


@pytest.mark.asyncio
async def test_start_cli_process_with_file_descriptors():
    """Test CLI process startup with file descriptor redirection."""
    mock_process = AsyncMock()
    mock_process.pid = 12345

    with patch("application.agents.shared.repository_tools.cli_process.asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("application.agents.shared.repository_tools.cli_process.get_process_manager") as mock_pm:
            mock_pm_instance = AsyncMock()
            mock_pm_instance.can_start_process = AsyncMock(return_value=True)
            mock_pm_instance.register_process = AsyncMock(return_value=True)
            mock_pm.return_value = mock_pm_instance

            with patch("application.agents.shared.repository_tools.cli_process.os.close") as mock_close:
                success, error_msg, process = await start_cli_process(
                    command=["bash", "script.sh"],
                    repository_path="/tmp/repo",
                    process_type="test",
                    stdout_fd=10,
                    stderr_fd=11,
                )

                assert success is True
                assert process == mock_process
                # Verify file descriptors were closed
                assert mock_close.call_count == 2


@pytest.mark.asyncio
async def test_setup_and_monitor_cli_process_success():
    """Test successful setup and monitoring of CLI process."""
    mock_process = AsyncMock()
    mock_process.pid = 12345

    mock_setup_tracking_fn = AsyncMock(return_value=("task_123", "env_456"))
    mock_start_monitoring_fn = AsyncMock()
    mock_tool_context = MagicMock()

    success, error_msg, task_id, env_task_id = await setup_and_monitor_cli_process(
        process=mock_process,
        repository_path="/tmp/repo",
        branch_name="test-branch",
        tool_context=mock_tool_context,
        setup_tracking_fn=mock_setup_tracking_fn,
        start_monitoring_fn=mock_start_monitoring_fn,
        process_type="test",
        extra_arg="extra_value",
    )

    assert success is True
    assert error_msg == ""
    assert task_id == "task_123"
    assert env_task_id == "env_456"

    # Verify functions were called with correct arguments
    mock_setup_tracking_fn.assert_called_once()
    mock_start_monitoring_fn.assert_called_once()


@pytest.mark.asyncio
async def test_setup_and_monitor_cli_process_tracking_fails():
    """Test setup and monitoring when tracking setup fails."""
    mock_process = AsyncMock()
    mock_process.pid = 12345

    mock_setup_tracking_fn = AsyncMock(side_effect=Exception("Tracking failed"))
    mock_start_monitoring_fn = AsyncMock()
    mock_tool_context = MagicMock()

    success, error_msg, task_id, env_task_id = await setup_and_monitor_cli_process(
        process=mock_process,
        repository_path="/tmp/repo",
        branch_name="test-branch",
        tool_context=mock_tool_context,
        setup_tracking_fn=mock_setup_tracking_fn,
        start_monitoring_fn=mock_start_monitoring_fn,
        process_type="test",
    )

    assert success is False
    assert "Failed to setup test tracking" in error_msg
    assert task_id is None
    assert env_task_id is None

    # Verify start_monitoring was NOT called if tracking failed
    mock_start_monitoring_fn.assert_not_called()


@pytest.mark.asyncio
async def test_setup_and_monitor_cli_process_monitoring_fails():
    """Test setup and monitoring when monitoring setup fails."""
    mock_process = AsyncMock()
    mock_process.pid = 12345

    mock_setup_tracking_fn = AsyncMock(return_value=("task_123", "env_456"))
    mock_start_monitoring_fn = AsyncMock(side_effect=Exception("Monitoring failed"))
    mock_tool_context = MagicMock()

    success, error_msg, task_id, env_task_id = await setup_and_monitor_cli_process(
        process=mock_process,
        repository_path="/tmp/repo",
        branch_name="test-branch",
        tool_context=mock_tool_context,
        setup_tracking_fn=mock_setup_tracking_fn,
        start_monitoring_fn=mock_start_monitoring_fn,
        process_type="test",
    )

    assert success is False
    assert "Failed to setup test tracking" in error_msg
    # Task was created but monitoring failed
    assert task_id is None
    assert env_task_id is None
