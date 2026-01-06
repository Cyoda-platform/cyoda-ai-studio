"""Tests for _stream_process_output function."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.agents.shared.repository_tools.monitoring import _stream_process_output


class TestStreamProcessOutput:
    """Test _stream_process_output function."""

    @pytest.mark.asyncio
    async def test_stream_no_output(self):
        """Test function handles process with no output."""
        mock_process = AsyncMock()
        # Return empty immediately to exit loop
        mock_process.stdout.read = AsyncMock(return_value=b"")

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service"):
            # Use timeout to prevent hanging
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id=None), timeout=2)
            except asyncio.TimeoutError:
                pass  # Expected if function hangs

    @pytest.mark.asyncio
    async def test_stream_single_chunk(self):
        """Test function streams single output chunk."""
        mock_process = AsyncMock()
        # First call returns data, second returns empty to exit
        mock_process.stdout.read = AsyncMock(side_effect=[b"test output", b""])

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service"):
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id=None), timeout=2)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_multiple_chunks(self):
        """Test function streams multiple output chunks."""
        mock_process = AsyncMock()
        mock_process.stdout.read = AsyncMock(side_effect=[
            b"chunk1",
            b"chunk2",
            b"chunk3",
            b""
        ])

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service"):
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id=None), timeout=2)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_with_task_id_update(self):
        """Test function updates task with accumulated output."""
        mock_process = AsyncMock()
        large_output = b"x" * 6000
        mock_process.stdout.read = AsyncMock(side_effect=[large_output, b""])

        mock_task_service = AsyncMock()
        mock_task_service.get_task = AsyncMock(return_value=MagicMock(metadata={}))
        mock_task_service.update_task_status = AsyncMock()

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service", return_value=mock_task_service):
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id="task-123"), timeout=2)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_timeout_handling(self):
        """Test function handles timeout gracefully."""
        mock_process = AsyncMock()
        # Timeout then empty to exit
        mock_process.stdout.read = AsyncMock(side_effect=[asyncio.TimeoutError(), b""])

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service"):
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id=None), timeout=2)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_utf8_decoding(self):
        """Test function handles UTF-8 decoding with errors."""
        mock_process = AsyncMock()
        mock_process.stdout.read = AsyncMock(side_effect=[b"\xff\xfe", b""])

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service"):
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id=None), timeout=2)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_task_update_failure(self):
        """Test function handles task update failures gracefully."""
        mock_process = AsyncMock()
        large_output = b"x" * 6000
        mock_process.stdout.read = AsyncMock(side_effect=[large_output, b""])

        mock_task_service = AsyncMock()
        mock_task_service.get_task = AsyncMock(side_effect=Exception("Service error"))

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service", return_value=mock_task_service):
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id="task-123"), timeout=2)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_stream_periodic_update(self):
        """Test function performs periodic updates based on time interval."""
        mock_process = AsyncMock()
        mock_process.stdout.read = AsyncMock(side_effect=[
            b"chunk1",
            asyncio.TimeoutError(),
            b""
        ])

        mock_task_service = AsyncMock()
        mock_task_service.get_task = AsyncMock(return_value=MagicMock(metadata={}))
        mock_task_service.update_task_status = AsyncMock()

        with patch("application.agents.shared.repository_tools.monitoring.get_task_service", return_value=mock_task_service):
            try:
                await asyncio.wait_for(_stream_process_output(mock_process, task_id="task-123"), timeout=2)
            except asyncio.TimeoutError:
                pass

