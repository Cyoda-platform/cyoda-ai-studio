"""File and output management for CLI processes.

This module handles temporary file creation, output logging,
and file renaming for CLI operations.
"""

from __future__ import annotations

import datetime
import logging
import os
import tempfile
from typing import Optional

from common.config.config import CLI_PROVIDER

logger = logging.getLogger(__name__)


def _write_prompt_to_tempfile(prompt: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Write prompt to temporary file for security.

    Args:
        prompt: Prompt content

    Returns:
        Tuple of (success, error_message, temp_file_path)
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, dir="/tmp"
        ) as f:
            f.write(prompt)
            prompt_file = f.name
        logger.info(f"📝 Prompt written to temp file: {prompt_file}")
        return True, None, prompt_file
    except Exception as e:
        logger.error(f"Failed to write prompt to temp file: {e}")
        error_msg = f"ERROR: Failed to write prompt to temp file: {e}"
        return False, error_msg, None


def _create_output_log_file(
    branch_name: str, process_type: str = "build"
) -> tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """Create output log file for CLI process.

    Args:
        branch_name: Branch name
        process_type: Type of process ("build" or "codegen")

    Returns:
        Tuple of (success, error_message, output_file_path, file_descriptor)
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = (
            f"{CLI_PROVIDER}_{process_type}_{branch_name}_TEMP_{timestamp}.log"
        )
        output_file = os.path.join("/tmp", output_filename)
        output_fd = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

        # Write header
        header = (
            f"{'Application Build' if process_type == 'build' else 'Code Generation'} Log\n"
            f"CLI Provider: {CLI_PROVIDER}\n"
            f"Branch: {branch_name}\n"
            f"Started: {timestamp}\n"
            f"{'=' * 80}\n\n"
        )
        os.write(output_fd, header.encode("utf-8"))
        logger.info(f"📝 Output log file created: {output_file}")

        return True, None, output_file, output_fd
    except Exception as e:
        logger.error(f"Failed to create output file: {e}")
        error_msg = f"ERROR: Failed to create output file: {e}"
        return False, error_msg, None, None


def _rename_output_file_with_pid(
    output_file: str, branch_name: str, pid: int, process_type: str = "build"
) -> str:
    """Rename output file to include PID.

    Args:
        output_file: Current output file path
        branch_name: Branch name
        pid: Process ID
        process_type: Type of process

    Returns:
        New output file path
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename_with_pid = (
            f"{CLI_PROVIDER}_{process_type}_{branch_name}_{pid}_{timestamp}.log"
        )
        output_file_with_pid = os.path.join("/tmp", output_filename_with_pid)
        os.rename(output_file, output_file_with_pid)
        logger.info(f"📝 Output log file renamed with PID: {output_file_with_pid}")
        return output_file_with_pid
    except Exception as e:
        logger.warning(f"⚠️ Failed to rename output file with PID: {e}")
        return output_file
