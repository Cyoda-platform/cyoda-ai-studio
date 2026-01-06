"""Tool for adding application resource files."""

from __future__ import annotations

import logging
import os

from google.adk.tools.tool_context import ToolContext

from ...common.utils.decorators import handle_tool_errors
from ..helpers._file_operations import (
    get_project_root,
    run_in_executor,
    validate_file_path,
    write_text_file,
)

logger = logging.getLogger(__name__)


@handle_tool_errors
async def add_application_resource(
    file_path: str,
    content: str,
    tool_context: ToolContext,
) -> str:
    """Add or update an application resource file.

    Creates a new file or updates an existing file with the provided content.
    Validates path security to prevent directory traversal attacks.

    Args:
        file_path: Relative path where the file should be created/updated
        content: Content to write to the file
        tool_context: Tool context containing session state

    Returns:
        Success message with file details, or error message
    """
    # Validate path security
    is_valid, error = validate_file_path(file_path)
    if not is_valid:
        return f"Error: {error}"

    # Get project root from session state or use current directory
    project_root = get_project_root(tool_context)

    # Construct full path
    full_path = os.path.join(project_root, file_path)

    # Create parent directories and write file (run in thread pool for async)
    await run_in_executor(write_text_file, full_path, content)

    character_count = len(content)
    logger.info(f"Added/updated application resource: {file_path} ({character_count} characters)")
    return f"Successfully added application resource: {file_path} ({character_count} characters)"
