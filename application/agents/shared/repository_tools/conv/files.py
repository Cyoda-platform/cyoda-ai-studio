"""File retrieval and decoding functions from conversation entities."""

import base64
import logging
from typing import Optional

from common.config.config import CYODA_ENTITY_TYPE_EDGE_MESSAGE
from application.entity.conversation.version_1.conversation import Conversation
from services.services import get_entity_service

logger = logging.getLogger(__name__)


def _collect_file_ids_from_conversation(conversation: Conversation) -> list[str]:
    """Collect file IDs from conversation entity.

    Checks conversation-level file_blob_ids first, then falls back to
    legacy chat_flow.finished_flow for backward compatibility.

    Args:
        conversation: Conversation entity.

    Returns:
        List of unique file IDs (duplicates removed).
    """
    file_ids: list[str] = []

    # Primary source: conversation-level file_blob_ids
    if hasattr(conversation, 'file_blob_ids') and conversation.file_blob_ids:
        file_ids.extend(conversation.file_blob_ids)
        logger.info(f"📎 Found {len(conversation.file_blob_ids)} files in conversation.file_blob_ids")
    else:
        # Fallback: legacy chat_flow for backward compatibility
        logger.info("📎 No conversation-level file_blob_ids, scanning messages...")
        has_chat_flow = (
            hasattr(conversation, 'chat_flow') and conversation.chat_flow and
            conversation.chat_flow.get("finished_flow")
        )
        if has_chat_flow:
            for message in conversation.chat_flow["finished_flow"]:
                if isinstance(message, dict) and message.get("file_blob_ids"):
                    file_ids.extend(message["file_blob_ids"])
                    file_count = len(message['file_blob_ids'])
                    msg_id = message.get('technical_id')
                    logger.info(f"📎 Found {file_count} files in message {msg_id}")

    # Remove duplicates while preserving order
    return list(dict.fromkeys(file_ids))


async def _retrieve_edge_message(file_id: str) -> Optional[dict]:
    """Retrieve edge message (file) from repository.

    Args:
        file_id: Technical ID of the edge message.

    Returns:
        Edge message data or None if not found.
    """
    try:
        logger.info(f"🔍 Retrieving edge message: {file_id}")
        from services.services import get_repository
        repository = get_repository()
        meta = {"type": CYODA_ENTITY_TYPE_EDGE_MESSAGE}

        edge_data = await repository.find_by_id(
            meta=meta,
            entity_id=file_id
        )

        if not edge_data:
            logger.warning(f"⚠️ Edge message {file_id} not found")
            return None

        logger.info(f"📥 Retrieved edge message {file_id}: {type(edge_data)}")
        return edge_data

    except Exception as e:
        logger.error(f"❌ Failed to retrieve edge message {file_id}: {e}", exc_info=True)
        return None


def _extract_filename_from_metadata(metadata: dict, index: int) -> str:
    """Extract filename from edge message metadata.

    Args:
        metadata: Edge message metadata dictionary.
        index: Index for generating default filename.

    Returns:
        Filename string.
    """
    if metadata and 'filename' in metadata:
        return metadata['filename']
    return f"file_{index + 1}.txt"


def _decode_file_content(base64_content: str, metadata: dict, filename: str) -> str:
    """Decode file content from base64 if needed.

    Args:
        base64_content: Potentially base64-encoded content.
        metadata: Edge message metadata.
        filename: Filename for logging.

    Returns:
        Decoded file content.
    """
    if not base64_content or metadata.get('encoding') != 'base64':
        return str(base64_content)

    try:
        decoded = base64.b64decode(base64_content).decode('utf-8')
        logger.info(f"✅ Decoded file: {filename} ({len(decoded)} chars)")
        return decoded
    except Exception as e:
        logger.error(f"❌ Failed to decode {filename}: {e}")
        return str(base64_content)


def _extract_file_from_edge_data(edge_data: dict, index: int) -> Optional[dict]:
    """Extract filename and content from edge message data.

    Args:
        edge_data: Edge message data (dict format).
        index: Index for generating default filename.

    Returns:
        Dictionary with 'filename' and 'content' keys, or None on error.
    """
    try:
        metadata = edge_data.get('metadata', {})
        filename = _extract_filename_from_metadata(metadata, index)
        base64_content = edge_data.get('message', '')
        file_content = _decode_file_content(base64_content, metadata, filename)

        return {"filename": filename, "content": file_content}

    except Exception as e:
        logger.error(f"❌ Failed to extract file from edge data: {e}")
        return None


def _extract_file_from_edge_object(edge_data: object, index: int) -> Optional[dict]:
    """Extract filename and content from edge message object.

    Args:
        edge_data: Edge message data (object format with message and metadata).
        index: Index for generating default filename.

    Returns:
        Dictionary with 'filename' and 'content' keys, or None on error.
    """
    try:
        if not hasattr(edge_data, 'message') or not hasattr(edge_data, 'metadata'):
            return None

        metadata = edge_data.metadata or {}
        filename = _extract_filename_from_metadata(metadata, index)
        base64_content = edge_data.message or ''
        file_content = _decode_file_content(base64_content, metadata, filename)

        return {"filename": filename, "content": file_content}

    except Exception as e:
        logger.error(f"❌ Failed to extract file from edge object: {e}")
        return None


async def _retrieve_and_decode_files(file_ids: list[str]) -> list[dict]:
    """Retrieve and decode all files from edge messages.

    Args:
        file_ids: List of file IDs to retrieve.

    Returns:
        List of dicts with 'filename' and 'content' keys.
    """
    files_to_save: list[dict[str, str]] = []

    for index, file_id in enumerate(file_ids):
        edge_data = await _retrieve_edge_message(file_id)
        if not edge_data:
            continue

        # Try dict format first
        if isinstance(edge_data, dict):
            file_dict = _extract_file_from_edge_data(edge_data, index)
            if file_dict:
                files_to_save.append(file_dict)
                logger.info(f"📎 Added file to save list: {file_dict['filename']}")
            continue

        # Try object format
        file_dict = _extract_file_from_edge_object(edge_data, index)
        if file_dict:
            files_to_save.append(file_dict)
            logger.info(f"📎 Added file to save list: {file_dict['filename']}")

    return files_to_save
