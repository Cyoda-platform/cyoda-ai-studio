"""Conversation CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from application.entity.conversation import Conversation
from application.repositories.conversation_repository import ConversationRepository

from .cache import ChatCacheManager

logger = logging.getLogger(__name__)


async def create_conversation(
    conversation_repo: ConversationRepository,
    cache_manager: ChatCacheManager,
    user_id: str,
    name: str,
    description: Optional[str] = None,
    file_blob_ids: Optional[List[str]] = None,
) -> Conversation:
    """Create a new conversation.

    Args:
        conversation_repo: Repository for conversation data access
        cache_manager: Cache manager for invalidation
        user_id: Owner user ID
        name: Conversation name
        description: Conversation description (optional)
        file_blob_ids: List of file blob IDs attached (optional)

    Returns:
        Created conversation

    Example:
        >>> conv = await create_conversation(
        ...     repo,
        ...     cache,
        ...     user_id="alice",
        ...     name="My Chat",
        ...     description="Test conversation"
        ... )
    """
    conversation = Conversation(
        user_id=user_id,
        name=name or "New Chat",
        description=description or "",
        file_blob_ids=file_blob_ids or [],
    )

    created = await conversation_repo.create(conversation)
    logger.info(f"Created conversation {created.technical_id} for user {user_id}")

    # Invalidate cache
    cache_manager.invalidate_cache(user_id)

    return created


async def get_conversation(
    conversation_repo: ConversationRepository, technical_id: str
) -> Optional[Conversation]:
    """Get conversation by ID.

    Args:
        conversation_repo: Repository for conversation data access
        technical_id: Conversation technical ID

    Returns:
        Conversation or None if not found

    Example:
        >>> conv = await get_conversation(repo, "123-456")
    """
    return await conversation_repo.get_by_id(technical_id)


async def update_conversation(
    conversation_repo: ConversationRepository,
    cache_manager: ChatCacheManager,
    conversation: Conversation,
) -> Conversation:
    """Update conversation with automatic retry on conflicts.

    Args:
        conversation_repo: Repository for conversation data access
        cache_manager: Cache manager for invalidation
        conversation: Conversation with updates

    Returns:
        Updated conversation

    Example:
        >>> conv.name = "Updated Name"
        >>> updated = await update_conversation(repo, cache, conv)
    """
    updated = await conversation_repo.update_with_retry(conversation)
    logger.info(f"Updated conversation {updated.technical_id}")

    # Invalidate cache
    cache_manager.invalidate_cache(updated.user_id)

    return updated


async def delete_conversation(
    conversation_repo: ConversationRepository,
    cache_manager: ChatCacheManager,
    technical_id: str,
    user_id: str,
) -> None:
    """Delete conversation.

    Args:
        conversation_repo: Repository for conversation data access
        cache_manager: Cache manager for invalidation
        technical_id: Conversation technical ID
        user_id: User ID for cache invalidation

    Example:
        >>> await delete_conversation(repo, cache, "123-456", "alice")
    """
    await conversation_repo.delete(technical_id)
    logger.info(f"Deleted conversation {technical_id}")

    # Invalidate cache
    cache_manager.invalidate_cache(user_id)


def validate_ownership(
    conversation: Conversation, user_id: str, is_superuser: bool = False
) -> None:
    """Validate that user has access to conversation.

    Args:
        conversation: Conversation to check
        user_id: Requesting user ID
        is_superuser: Whether user has superuser privileges

    Raises:
        PermissionError: If user doesn't have access

    Example:
        >>> validate_ownership(conv, "alice", False)
    """
    if is_superuser:
        return

    if conversation.user_id != user_id:
        raise PermissionError(
            f"User {user_id} does not have access to chat {conversation.technical_id}"
        )


async def transfer_guest_chats(
    conversation_repo: ConversationRepository,
    cache_manager: ChatCacheManager,
    guest_user_id: str,
    authenticated_user_id: str,
) -> int:
    """Transfer chats from guest user to authenticated user.

    Args:
        conversation_repo: Repository for conversation data access
        cache_manager: Cache manager for invalidation
        guest_user_id: Guest user ID (must start with 'guest.')
        authenticated_user_id: Authenticated user ID (must not start with 'guest.')

    Returns:
        Number of chats transferred

    Raises:
        ValueError: If user IDs are invalid

    Example:
        >>> count = await transfer_guest_chats(repo, cache, "guest.123", "alice")
        >>> print(f"Transferred {count} chats")
    """
    # Validate user IDs
    if not guest_user_id.startswith("guest."):
        raise ValueError("Source user must be a guest user")
    if authenticated_user_id.startswith("guest."):
        raise ValueError("Cannot transfer chats to guest user")

    logger.info(
        f"🔄 Starting chat transfer from {guest_user_id} to {authenticated_user_id}"
    )

    # Find all guest chats
    guest_chats = await conversation_repo.search(user_id=guest_user_id)

    transferred_count = 0
    for chat_response in guest_chats:
        if hasattr(chat_response, "metadata"):
            conversation = await conversation_repo.get_by_id(chat_response.metadata.id)
            if conversation:
                conversation.user_id = authenticated_user_id
                await conversation_repo.update_with_retry(conversation)
                transferred_count += 1
                logger.debug(f"✅ Transferred chat {conversation.technical_id}")

    # Invalidate caches
    cache_manager.invalidate_cache(guest_user_id)
    cache_manager.invalidate_cache(authenticated_user_id)

    logger.info(
        f"✅ Chat transfer completed: {transferred_count} chats transferred "
        f"from {guest_user_id} to {authenticated_user_id}"
    )

    return transferred_count
