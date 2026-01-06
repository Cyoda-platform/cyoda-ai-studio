"""Tool for listing directory files."""

from __future__ import annotations

import logging
import os

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.common_formatters import format_error
from ...common.formatters.file_formatters import format_file_list
from ...common.utils.decorators import handle_tool_errors
from ..helpers._file_operations import get_project_root, run_in_executor, walk_directory

logger = logging.getLogger(__name__)


@handle_tool_errors
async def list_directory_files(
    directory_path: str,
    tool_context: ToolContext,
) -> str:
    """List all files recursively in a directory.

    Walks through the directory tree and returns a list of all files found,
    excluding common directories like .git, .venv, __pycache__, etc.

    Args:
        directory_path: Relative path to the directory to list
        tool_context: Tool context containing session state

    Returns:
        JSON string with list of files or error message
    """
    # Get project root from session state or use current directory
    project_root = get_project_root(tool_context)

    # Construct full path
    full_path = os.path.join(project_root, directory_path)

    # Validate path exists
    if not os.path.exists(full_path):
        return format_error(f"Directory not found: {directory_path}")

    if not os.path.isdir(full_path):
        return format_error(f"Path is not a directory: {directory_path}")

    # Collect all files recursively (run in thread pool for large directories)
    all_files = await run_in_executor(walk_directory, full_path, project_root)

    logger.info(f"Listed {len(all_files)} files in {directory_path}")
    return format_file_list(all_files, len(all_files))
