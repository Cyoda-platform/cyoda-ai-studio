"""
Conversation management functions for repository tools.

This module handles conversation entity updates with pessimistic locking,
build context management, task tracking, and file retrieval from conversations.

Internal organization:
- conv/locking.py: Lock acquisition and release
- conv/updates.py: Conversation update with verification
- conv/management.py: Build context and task management
- conv/files.py: File retrieval and decoding
"""

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from services.services import get_entity_service

# Re-export from conv modules for backward compatibility
from .conv import (
    _fetch_conversation,
    _acquire_lock,
    _release_lock,
    _calculate_next_retry_delay,
    _persist_and_verify_update,
    _update_conversation_with_lock,
    _apply_update_and_persist,
    _update_conversation_build_context,
    _add_task_to_conversation,
    _validate_tool_context,
    _get_conversation_entity,
    _collect_file_ids_from_conversation,
    _retrieve_edge_message,
    _extract_filename_from_metadata,
    _decode_file_content,
    _extract_file_from_edge_data,
    _extract_file_from_edge_object,
    _retrieve_and_decode_files,
)
from .conv.files import _collect_file_ids_from_conversation, _retrieve_and_decode_files
from .conv.management import _get_conversation_entity, _validate_tool_context

logger = logging.getLogger(__name__)


async def retrieve_and_save_conversation_files(
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Retrieve files from conversation and save to branch.

    Retrieves files that were attached at conversation start (before branch creation)
    from the Conversation entity and saves them to the functional requirements directory.

    Args:
        tool_context: Execution context (auto-injected).

    Returns:
        Status message indicating success or error.
    """
    try:
        # Validate context and extract conversation ID
        conversation_id = _validate_tool_context(tool_context)
        logger.info(f"📂 Retrieving files from conversation {conversation_id}")

        # Fetch conversation entity
        conversation = await _get_conversation_entity(conversation_id)
        if not conversation:
            return f"ERROR: Conversation {conversation_id} not found"

        # Collect file IDs from conversation
        file_ids = _collect_file_ids_from_conversation(conversation)
        if not file_ids:
            logger.warning("⚠️ No files found in conversation entity")
            return (
                "No files found in conversation. If you attached a file, it may not have been "
                "saved to the conversation entity yet. Please try providing the file content directly, "
                "or check if the file was successfully uploaded."
            )

        logger.info(f"📂 Total unique files to retrieve: {len(file_ids)}: {file_ids}")

        # Retrieve and decode files from edge messages
        files_to_save = await _retrieve_and_decode_files(file_ids)
        if not files_to_save:
            return "ERROR: No valid files could be retrieved from conversation"

        # Save files to branch
        logger.info(f"💾 Saving {len(files_to_save)} files to branch...")
        from application.agents.shared.repository_tools.files import save_files_to_branch
        return await save_files_to_branch(files=files_to_save, tool_context=tool_context)

    except ValueError as e:
        error_msg = str(e)
        logger.error(f"❌ Validation error: {error_msg}")
        return f"ERROR: {error_msg}"
    except Exception as e:
        logger.error(f"❌ Failed to retrieve and save conversation files: {e}", exc_info=True)
        return f"ERROR: Failed to retrieve and save conversation files: {str(e)}"


__all__ = [
    # Public API
    "retrieve_and_save_conversation_files",
    # Service dependencies (for test mocking)
    "get_entity_service",
    # Re-exported for backward compatibility
    "_fetch_conversation",
    "_acquire_lock",
    "_release_lock",
    "_calculate_next_retry_delay",
    "_persist_and_verify_update",
    "_update_conversation_with_lock",
    "_apply_update_and_persist",
    "_update_conversation_build_context",
    "_add_task_to_conversation",
    "_validate_tool_context",
    "_get_conversation_entity",
    "_collect_file_ids_from_conversation",
    "_retrieve_edge_message",
    "_extract_filename_from_metadata",
    "_decode_file_content",
    "_extract_file_from_edge_data",
    "_extract_file_from_edge_object",
    "_retrieve_and_decode_files",
]
