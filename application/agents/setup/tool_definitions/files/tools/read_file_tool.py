"""Tool for reading file contents."""

from __future__ import annotations

import logging
import os

from google.adk.tools.tool_context import ToolContext

from ...common.utils.decorators import handle_tool_errors
from ..helpers._file_operations import (
    get_project_root,
    read_text_file,
    run_in_executor,
    validate_file_path,
)

logger = logging.getLogger(__name__)


@handle_tool_errors
async def read_file(
    file_path: str,
    tool_context: ToolContext,
) -> str:
    """Read the contents of a file.

    Args:
        file_path: Relative path to the file to read
        tool_context: Tool context containing session state

    Returns:
        File contents as string, or error message
    """
    # Validate path security
    is_valid, error = validate_file_path(file_path)
    if not is_valid:
        return f"Error: {error}"

    # Get project root from session state or use current directory
    project_root = get_project_root(tool_context)

    # Construct full path
    full_path = os.path.join(project_root, file_path)

    if not os.path.exists(full_path):
        return f"Error: File not found: {file_path}"

    if not os.path.isfile(full_path):
        return f"Error: Path is not a file: {file_path}"

    # Read file contents (run in thread pool for async)
    try:
        content = await run_in_executor(read_text_file, full_path)
        logger.info(f"Read file: {file_path} ({len(content)} characters)")
        return content
    except UnicodeDecodeError:
        return f"Error: File is not a text file or uses unsupported encoding: {file_path}"
