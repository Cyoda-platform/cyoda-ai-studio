"""Helper functions for file operations."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Callable

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import DEFAULT_ENCODING, EXCLUDED_DIRECTORIES

logger = logging.getLogger(__name__)


def get_project_root(tool_context: ToolContext) -> str:
    """Get project root from session state or current directory.

    Args:
        tool_context: Tool context containing session state

    Returns:
        Project root directory path
    """
    return tool_context.state.get("project_path", os.getcwd())


def validate_file_path(file_path: str) -> tuple[bool, str | None]:
    """Validate file path for security.

    Args:
        file_path: File path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if ".." in file_path or file_path.startswith("/"):
        return False, "Invalid file path. Path must be relative and not contain '..'"

    return True, None


async def run_in_executor(func: Callable, *args) -> any:
    """Run a blocking function in executor for async compatibility.

    Args:
        func: Blocking function to run
        *args: Arguments to pass to function

    Returns:
        Function result
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


def walk_directory(root_path: str, project_root: str) -> list[str]:
    """Walk directory tree and collect file paths.

    Args:
        root_path: Root directory to walk
        project_root: Project root for relative paths

    Returns:
        List of relative file paths
    """
    all_files = []

    for root, dirs, files in os.walk(root_path):
        # Remove excluded directories from traversal
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRECTORIES]

        # Add files with relative paths
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, project_root)
            all_files.append(relative_path)

    return all_files


def read_text_file(file_path: str) -> str:
    """Read text file contents.

    Args:
        file_path: Path to file to read

    Returns:
        File contents

    Raises:
        UnicodeDecodeError: If file is not text or uses unsupported encoding
    """
    with open(file_path, "r", encoding=DEFAULT_ENCODING) as f:
        return f.read()


def write_text_file(file_path: str, content: str) -> None:
    """Write content to text file.

    Args:
        file_path: Path to file to write
        content: Content to write
    """
    # Create parent directories if needed
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(file_path, "w", encoding=DEFAULT_ENCODING) as f:
        f.write(content)
