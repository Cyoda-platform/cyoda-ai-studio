"""Tool for saving files to repository.

This module handles file saving operations with automatic repository cloning
and canvas tab integration.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from ...common.constants import STOP_ON_ERROR
from ...common.utils import ensure_repository_available

logger = logging.getLogger(__name__)

# File save constants
REPOSITORY_PATH_NOT_FOUND_ERROR = "ERROR: repository_path not found in context. Repository must be cloned first.{stop}"
REPOSITORY_UNAVAILABLE_ERROR = "ERROR: {message}{stop}"
SUCCESS_MESSAGE_TEMPLATE = "SUCCESS: File saved to {file_path}"
CANVAS_SUCCESS_TEMPLATE = "✅ File saved to {file_path}\n\n📂 Opening Canvas {tab_name} tab to view your changes."
CANVAS_TAB_MAPPING = {
    "entity": "entities",
    "workflow": "workflows",
    "requirement": "requirements",
}
FILE_SAVE_LOG_TEMPLATE = "Saved file: {file_path}"
FILE_SAVE_ERROR_TEMPLATE = "Error saving file {file_path}: {error}"


class FileLocation(BaseModel):
    """File location and metadata."""

    file_path: str
    full_path: Path
    canvas_tab_name: Optional[str] = None


class SaveFileContext(BaseModel):
    """Context for file saving operation."""

    repository_path: str
    file_path: str
    content: str
    conversation_id: Optional[str] = None


async def _extract_save_context(
    file_path: str, content: str, tool_context: ToolContext
) -> Tuple[bool, Optional[str], Optional[SaveFileContext]]:
    """Extract and validate save file context from tool context.

    Args:
        file_path: Relative file path
        content: File content to save
        tool_context: The ADK tool context

    Returns:
        Tuple of (is_valid, error_message, save_context)
    """
    repository_path = tool_context.state.get("repository_path")
    if not repository_path:
        error = REPOSITORY_PATH_NOT_FOUND_ERROR.format(stop=STOP_ON_ERROR)
        return False, error, None

    conversation_id = tool_context.state.get("conversation_id")

    context = SaveFileContext(
        repository_path=repository_path,
        file_path=file_path,
        content=content,
        conversation_id=conversation_id,
    )

    return True, None, context


async def _ensure_repository_ready(
    save_context: SaveFileContext, tool_context: ToolContext
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Ensure repository is available locally.

    Args:
        save_context: File save context
        tool_context: The ADK tool context

    Returns:
        Tuple of (is_valid, error_message, repository_path)
    """
    success, message, repository_path = await ensure_repository_available(
        repository_path=save_context.repository_path,
        tool_context=tool_context,
        require_git=True,
    )

    if not success:
        error = REPOSITORY_UNAVAILABLE_ERROR.format(message=message, stop=STOP_ON_ERROR)
        return False, error, None

    return True, None, repository_path


def _detect_canvas_tab_name(file_path: str) -> Optional[str]:
    """Detect canvas tab name from file path.

    Args:
        file_path: File path to analyze

    Returns:
        Canvas tab name if detected, None otherwise
    """
    file_lower = file_path.lower()

    for key, tab_name in CANVAS_TAB_MAPPING.items():
        if f"/{key}/" in file_lower:
            return tab_name

    return None


async def _write_file_to_disk(full_path: Path, content: str) -> None:
    """Write file to disk asynchronously.

    Args:
        full_path: Full path to file
        content: File content to write
    """
    def _write():
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _write)


async def _create_canvas_hook_response(
    save_context: SaveFileContext, tab_name: str, tool_context: ToolContext
) -> Optional[str]:
    """Create canvas hook and return formatted response.

    Args:
        save_context: File save context
        tab_name: Canvas tab name
        tool_context: The ADK tool context

    Returns:
        Formatted response with hook, or None if hook couldn't be created
    """
    if not save_context.conversation_id:
        return None

    from application.agents.shared.hooks import (
        create_open_canvas_tab_hook,
        wrap_response_with_hook,
    )

    hook = create_open_canvas_tab_hook(
        conversation_id=save_context.conversation_id,
        tab_name=tab_name,
    )

    # Store hook in context for SSE streaming
    tool_context.state["last_tool_hook"] = hook

    message = CANVAS_SUCCESS_TEMPLATE.format(
        file_path=save_context.file_path,
        tab_name=tab_name.title(),
    )
    return wrap_response_with_hook(message, hook)


async def save_file_to_repository(
    file_path: str, content: str, tool_context: ToolContext
) -> str:
    """Save a file to the repository (no path restrictions).

    Args:
        file_path: Relative path from repository root (e.g., "application/entity/order/version_1/order.json")
        content: File content to save
        tool_context: The ADK tool context

    Returns:
        Success or error message with canvas tab hook if applicable

    Example:
        >>> result = await save_file_to_repository(
        ...     file_path="src/main.py",
        ...     content="print('hello')",
        ...     tool_context=context
        ... )
    """
    try:
        # Step 1: Extract and validate save context
        is_valid, error_msg, save_context = await _extract_save_context(
            file_path, content, tool_context
        )
        if not is_valid:
            return error_msg

        # Step 2: Ensure repository is available
        is_ready, error_msg, repository_path = await _ensure_repository_ready(
            save_context, tool_context
        )
        if not is_ready:
            return error_msg

        # Step 3: Construct full path and write file
        full_path = Path(repository_path) / file_path
        await _write_file_to_disk(full_path, content)
        logger.info(FILE_SAVE_LOG_TEMPLATE.format(file_path=file_path))

        # Step 4: Detect canvas tab and create hook if applicable
        tab_name = _detect_canvas_tab_name(file_path)
        if tab_name:
            hook_response = await _create_canvas_hook_response(
                save_context, tab_name, tool_context
            )
            if hook_response:
                return hook_response

        # Step 5: Return success message
        return SUCCESS_MESSAGE_TEMPLATE.format(file_path=file_path)

    except Exception as e:
        logger.error(FILE_SAVE_ERROR_TEMPLATE.format(file_path=file_path, error=e), exc_info=True)
        return f"ERROR: {str(e)}{STOP_ON_ERROR}"
