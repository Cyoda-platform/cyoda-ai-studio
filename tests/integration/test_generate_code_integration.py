"""Integration tests for code generation with actual CLI process monitoring."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management import (
    _start_and_register_process,
    _create_and_setup_background_task,
)


@pytest.mark.asyncio
async def test_start_and_register_process_creates_output_file():
    """Test that _start_and_register_process creates output file and starts process."""
    mock_context = MagicMock()
    mock_context.branch_name = "test-branch"
    mock_context.repository_path = "/tmp/repo"

    mock_process = AsyncMock()
    mock_process.pid = 12345

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as prompt_file:
        prompt_path = prompt_file.name

    try:
        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._create_output_log_file"
        ) as mock_create_log:
            mock_create_log.return_value = (True, "", "/tmp/output.log", 10)

            with patch(
                "application.agents.shared.repository_tools.cli_process.start_cli_process"
            ) as mock_start_process:
                mock_start_process.return_value = (True, "", mock_process)

                with patch(
                    "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._rename_output_file_with_pid"
                ) as mock_rename:
                    mock_rename.return_value = "/tmp/output_12345.log"

                    success, error_msg, process, output_file = await _start_and_register_process(
                        mock_context,
                        Path("/tmp/script.sh"),
                        "test-model",
                        prompt_path,
                    )

                    assert success is True
                    assert error_msg == ""
                    assert process == mock_process
                    assert output_file == "/tmp/output_12345.log"
                    assert process.pid == 12345

    finally:
        Path(prompt_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_create_and_setup_background_task_with_monitoring():
    """Test that background task creation properly sets up monitoring."""
    mock_context = MagicMock()
    mock_context.branch_name = "test-branch"
    mock_context.repository_path = "/tmp/repo"
    mock_context.tool_context = MagicMock()
    mock_context.language = "python"
    mock_context.conversation_id = "conv-123"

    mock_process = AsyncMock()
    mock_process.pid = 12345

    with patch(
        "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._setup_codegen_tracking"
    ) as mock_setup_tracking:
        mock_setup_tracking.return_value = ("task-123", None)

        async def async_monitoring_task(**kwargs):
            await asyncio.sleep(0)
            return None

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._start_monitoring_task",
            side_effect=async_monitoring_task
        ):
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._create_codegen_hook"
            ) as mock_create_hook:
                mock_create_hook.return_value = {"type": "hook"}

                task_id, hook = await _create_and_setup_background_task(
                    mock_context,
                    mock_process,
                    "/tmp/prompt.txt",
                    "/tmp/output.log",
                    "Test request",
                )

                assert task_id == "task-123"
                assert hook == {"type": "hook"}

                # Verify hook was created
                mock_create_hook.assert_called_once()


@pytest.mark.asyncio
async def test_monitoring_task_actually_starts():
    """Test that the monitoring wrapper properly awaits the monitoring task."""
    from application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management import (
        _create_and_setup_background_task,
    )

    mock_context = MagicMock()
    mock_context.branch_name = "test-branch"
    mock_context.repository_path = "/tmp/repo"
    mock_context.tool_context = MagicMock()
    mock_context.language = "python"
    mock_context.conversation_id = "conv-123"

    mock_process = AsyncMock()
    mock_process.pid = 12345

    monitoring_called = False
    monitoring_awaited = False

    async def mock_monitoring_task(**kwargs):
        """Mock monitoring task that tracks if it's called and awaited."""
        nonlocal monitoring_awaited
        monitoring_awaited = True
        await asyncio.sleep(0.01)  # Simulate some work
        return None

    with patch(
        "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._setup_codegen_tracking"
    ) as mock_setup_tracking:
        mock_setup_tracking.return_value = ("task-123", None)

        with patch(
            "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._start_monitoring_task",
            side_effect=mock_monitoring_task,
        ) as mock_start_monitoring:
            with patch(
                "application.agents.github.tool_definitions.code_generation.tools.generate_code_tool.process_management._create_codegen_hook"
            ) as mock_create_hook:
                mock_create_hook.return_value = {}

                task_id, hook = await _create_and_setup_background_task(
                    mock_context,
                    mock_process,
                    "/tmp/prompt.txt",
                    "/tmp/output.log",
                    "Test request",
                )

                # Verify the monitoring task was actually awaited
                assert monitoring_awaited is True
                assert task_id == "task-123"
