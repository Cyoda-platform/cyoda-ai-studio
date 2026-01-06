"""Conversation management module - backward compatibility re-exports."""

from .locking import (
    _fetch_conversation,
    _acquire_lock,
    _release_lock,
    _calculate_next_retry_delay,
)
from .updates import (
    _persist_and_verify_update,
    _update_conversation_with_lock,
    _apply_update_and_persist,
)
from .management import (
    _update_conversation_build_context,
    _add_task_to_conversation,
    _validate_tool_context,
    _get_conversation_entity,
)
from .files import (
    _collect_file_ids_from_conversation,
    _retrieve_edge_message,
    _extract_filename_from_metadata,
    _decode_file_content,
    _extract_file_from_edge_data,
    _extract_file_from_edge_object,
    _retrieve_and_decode_files,
)

__all__ = [
    # Locking
    "_fetch_conversation",
    "_acquire_lock",
    "_release_lock",
    "_calculate_next_retry_delay",
    # Updates
    "_persist_and_verify_update",
    "_update_conversation_with_lock",
    "_apply_update_and_persist",
    # Management
    "_update_conversation_build_context",
    "_add_task_to_conversation",
    "_validate_tool_context",
    "_get_conversation_entity",
    # Files
    "_collect_file_ids_from_conversation",
    "_retrieve_edge_message",
    "_extract_filename_from_metadata",
    "_decode_file_content",
    "_extract_file_from_edge_data",
    "_extract_file_from_edge_object",
    "_retrieve_and_decode_files",
]
