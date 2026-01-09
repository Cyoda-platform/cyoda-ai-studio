"""Integration tests for CLI process startup and monitoring."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from application.agents.shared.repository_tools.cli_process import start_cli_process


@pytest.mark.asyncio
async def test_start_cli_process_actual_subprocess():
    """Test starting a real subprocess and verifying it runs."""
    # Create a simple test script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write('#!/bin/bash\necho "test output"\nexit 0\n')
        script_path = f.name

    try:
        # Make the script executable
        import os

        os.chmod(script_path, 0o755)

        # Start the process
        success, error_msg, process = await start_cli_process(
            command=["bash", script_path],
            repository_path="/tmp",
            process_type="test",
        )

        assert success is True
        assert error_msg == ""
        assert process is not None
        assert process.pid > 0

        # Wait for process to complete
        await process.wait()

        # Verify process completed successfully
        assert process.returncode == 0

    finally:
        # Cleanup
        import os

        if Path(script_path).exists():
            os.unlink(script_path)


@pytest.mark.asyncio
async def test_start_cli_process_with_error():
    """Test starting a subprocess that fails."""
    # Create a test script that fails
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write("#!/bin/bash\nexit 1\n")
        script_path = f.name

    try:
        # Make the script executable
        import os

        os.chmod(script_path, 0o755)

        # Start the process
        success, error_msg, process = await start_cli_process(
            command=["bash", script_path],
            repository_path="/tmp",
            process_type="test",
        )

        assert success is True  # Process started successfully
        assert process is not None

        # Wait for process to complete
        await process.wait()

        # Verify process failed
        assert process.returncode == 1

    finally:
        # Cleanup
        import os

        if Path(script_path).exists():
            os.unlink(script_path)


@pytest.mark.asyncio
async def test_start_cli_process_file_output():
    """Test starting a subprocess with file descriptor output."""
    import os
    import tempfile

    # Create output files
    with tempfile.NamedTemporaryFile(delete=False) as stdout_file:
        stdout_path = stdout_file.name

    with tempfile.NamedTemporaryFile(delete=False) as stderr_file:
        stderr_path = stderr_file.name

    # Create a test script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write('#!/bin/bash\necho "stdout message"\necho "stderr message" >&2\n')
        script_path = f.name

    try:
        os.chmod(script_path, 0o755)

        # Open file descriptors
        stdout_fd = os.open(stdout_path, os.O_WRONLY | os.O_CREAT)
        stderr_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT)

        # Start the process with file descriptors
        success, error_msg, process = await start_cli_process(
            command=["bash", script_path],
            repository_path="/tmp",
            process_type="test",
            stdout_fd=stdout_fd,
            stderr_fd=stderr_fd,
        )

        assert success is True
        assert process is not None

        # Wait for process to complete
        await process.wait()

        # Check output files contain data
        with open(stdout_path, "r") as f:
            stdout_content = f.read()
            assert len(stdout_content) > 0

    finally:
        # Cleanup
        for path in [script_path, stdout_path, stderr_path]:
            if Path(path).exists():
                os.unlink(path)
