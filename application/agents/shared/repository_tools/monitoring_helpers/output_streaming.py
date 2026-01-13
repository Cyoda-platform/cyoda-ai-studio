"""Process output streaming for background tasks.

This module handles streaming process output and updating task metadata.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from pydantic import BaseModel

from services.services import get_task_service

logger = logging.getLogger(__name__)

# Configuration constants for output streaming
STREAM_READ_CHUNK_SIZE = 1024  # Read 1KB at a time
STREAM_READ_TIMEOUT_SECONDS = 0.5  # Timeout for reading from stdout
UPDATE_INTERVAL_SECONDS = 2  # Update every 2 seconds or 5KB
UPDATE_SIZE_THRESHOLD = 5120  # 5KB threshold
KEEP_LAST_OUTPUT_BYTES = 10000  # Keep last 10KB of output


class OutputStreamState(BaseModel):
    """State for process output streaming."""

    accumulated_output: list = []
    last_update_time: float = 0.0
    accumulated_size: int = 0


async def _read_process_output_chunk(process: Any) -> Optional[str]:
    """Read one chunk of output from process stdout.

    Args:
        process: The asyncio subprocess

    Returns:
        Decoded output string or None if EOF
    """
    try:
        chunk = await asyncio.wait_for(
            process.stdout.read(STREAM_READ_CHUNK_SIZE),
            timeout=STREAM_READ_TIMEOUT_SECONDS,
        )
        if chunk:
            output_str = chunk.decode("utf-8", errors="replace")
            logger.debug(f"📤 Output chunk: {output_str[:100]}...")
            return output_str
        return None
    except asyncio.TimeoutError:
        return "TIMEOUT"  # Special marker for timeout


async def _should_update_task(
    accumulated_size: int, last_update_time: float, current_time: float
) -> bool:
    """Determine if task should be updated based on size or time interval.

    Args:
        accumulated_size: Bytes accumulated since last update
        last_update_time: Timestamp of last update
        current_time: Current timestamp

    Returns:
        True if update should happen
    """
    size_threshold_met = accumulated_size > UPDATE_SIZE_THRESHOLD
    time_threshold_met = (current_time - last_update_time) > UPDATE_INTERVAL_SECONDS
    return size_threshold_met or time_threshold_met


async def _update_task_with_output(
    task_id: str, accumulated_output: list, task_service: Any
) -> bool:
    """Update task with accumulated output.

    Args:
        task_id: BackgroundTask ID
        accumulated_output: List of output strings
        task_service: Task service instance

    Returns:
        True if update succeeded
    """
    try:
        full_output = "".join(accumulated_output)
        current_task = await task_service.get_task(task_id)
        existing_metadata = current_task.metadata if current_task else {}

        # Merge existing metadata with new output (keep last 10KB)
        updated_metadata = {
            **existing_metadata,
            "output": full_output[-KEEP_LAST_OUTPUT_BYTES:],
        }

        await task_service.update_task_status(
            task_id=task_id,
            metadata=updated_metadata,
        )
        logger.info(
            f"📤 Updated task {task_id} with {len(full_output)} bytes of output"
        )
        return True
    except Exception as e:
        logger.debug(f"Could not update task output: {e}")
        return False


async def _stream_process_output(
    process: Any,
    task_id: Optional[str] = None,
) -> None:
    """Stream process output chunks as they arrive.

    Reads from stdout and stderr, updates BackgroundTask with output chunks.
    Updates are batched to avoid excessive task service calls:
    - Every 5KB of accumulated output
    - Every 2 seconds

    Args:
        process: The asyncio subprocess
        task_id: BackgroundTask ID for storing output
    """
    try:
        task_service = get_task_service()
        accumulated_output = []
        last_update_time = asyncio.get_event_loop().time()

        # Main streaming loop - read and batch output updates
        while True:
            # Step 1: Read next chunk from process output
            output_chunk = await _read_process_output_chunk(process)

            if output_chunk == "TIMEOUT":
                # Step 2a: Handle timeout - check for periodic update
                current_time = asyncio.get_event_loop().time()
                accumulated_size = sum(len(s) for s in accumulated_output)

                if accumulated_output and task_id:
                    should_update = await _should_update_task(
                        accumulated_size, last_update_time, current_time
                    )
                    if should_update:
                        success = await _update_task_with_output(
                            task_id, accumulated_output, task_service
                        )
                        if success:
                            accumulated_output = []
                            last_update_time = current_time

            elif output_chunk is None:
                # Step 2b: EOF reached, exit loop
                break

            else:
                # Step 2c: Got data, accumulate and check for update
                accumulated_output.append(output_chunk)
                current_time = asyncio.get_event_loop().time()
                accumulated_size = sum(len(s) for s in accumulated_output)

                if task_id:
                    should_update = await _should_update_task(
                        accumulated_size, last_update_time, current_time
                    )
                    if should_update:
                        success = await _update_task_with_output(
                            task_id, accumulated_output, task_service
                        )
                        if success:
                            accumulated_output = []
                            last_update_time = current_time

        # Step 3: Final update with any remaining output
        if accumulated_output and task_id:
            await _update_task_with_output(task_id, accumulated_output, task_service)
            logger.info(f"📤 Final output update completed")

    except Exception as e:
        logger.warning(f"Error streaming process output: {e}")
