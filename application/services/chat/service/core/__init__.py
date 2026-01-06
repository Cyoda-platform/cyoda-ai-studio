"""Chat service core - Re-exports for backward compatibility."""

from .models import PaginationResult, CacheResult
from .constants import (
    FIELD_DATE,
    FIELD_TECHNICAL_ID,
    FIELD_NAME,
    FIELD_DESCRIPTION,
    FIELD_CREATED_AT,
    RESPONSE_KEY_CHATS,
    RESPONSE_KEY_LIMIT,
    RESPONSE_KEY_NEXT_CURSOR,
    RESPONSE_KEY_HAS_MORE,
    RESPONSE_KEY_CACHED,
)
from .cache import ChatCacheManager
from .formatters import (
    calculate_pagination,
    format_response,
    extract_conversations_from_response,
)
from .conversation_operations import (
    create_conversation,
    get_conversation,
    update_conversation,
    delete_conversation,
    validate_ownership,
    transfer_guest_chats,
)
from .list_operations import list_conversations


class ChatService:
    """Service for chat/conversation business operations.

    Provides high-level conversation management with caching and validation.
    """

    def __init__(self, conversation_repository, persistence_service):
        """Initialize chat service.

        Args:
            conversation_repository: Repository for conversation data access
            persistence_service: Service for edge message persistence
        """
        self.conversation_repo = conversation_repository
        self.persistence_service = persistence_service
        self.cache_manager = ChatCacheManager()

    async def create_conversation(
        self, user_id, name, description=None, file_blob_ids=None
    ):
        """Create a new conversation."""
        return await create_conversation(
            self.conversation_repo,
            self.cache_manager,
            user_id,
            name,
            description,
            file_blob_ids,
        )

    async def get_conversation(self, technical_id):
        """Get conversation by ID."""
        return await get_conversation(self.conversation_repo, technical_id)

    async def update_conversation(self, conversation):
        """Update conversation with automatic retry on conflicts."""
        return await update_conversation(
            self.conversation_repo, self.cache_manager, conversation
        )

    async def delete_conversation(self, technical_id, user_id):
        """Delete conversation."""
        await delete_conversation(
            self.conversation_repo, self.cache_manager, technical_id, user_id
        )

    def _calculate_pagination(self, chats, limit):
        """Calculate pagination info from chat list."""
        return calculate_pagination(chats, limit)

    def _format_response(self, chats, pagination, cached):
        """Format final response with all metadata."""
        return format_response(chats, pagination, cached)

    def _extract_conversations_from_response(self, response_list):
        """Extract conversation summaries from entity service response."""
        return extract_conversations_from_response(response_list)

    async def list_conversations(
        self, user_id=None, limit=50, before=None, use_cache=True
    ):
        """List conversations with pagination and caching."""
        return await list_conversations(
            self.conversation_repo,
            self.cache_manager,
            user_id,
            limit,
            before,
            use_cache,
        )

    async def count_user_chats(self, user_id):
        """Count the number of chats for a specific user."""
        result = await self.list_conversations(
            user_id=user_id,
            limit=1000,  # High enough limit to get all chats
            use_cache=False  # Don't use cache for counts
        )
        return len(result.get("chats", []))

    def validate_ownership(self, conversation, user_id, is_superuser=False):
        """Validate that user has access to conversation."""
        validate_ownership(conversation, user_id, is_superuser)

    async def transfer_guest_chats(self, guest_user_id, authenticated_user_id):
        """Transfer chats from guest user to authenticated user."""
        return await transfer_guest_chats(
            self.conversation_repo,
            self.cache_manager,
            guest_user_id,
            authenticated_user_id,
        )

    def invalidate_cache(self, user_id):
        """Invalidate chat list cache for user."""
        self.cache_manager.invalidate_cache(user_id)


__all__ = [
    "ChatService",
    "PaginationResult",
    "CacheResult",
    "ChatCacheManager",
    "FIELD_DATE",
    "FIELD_TECHNICAL_ID",
    "FIELD_NAME",
    "FIELD_DESCRIPTION",
    "FIELD_CREATED_AT",
    "RESPONSE_KEY_CHATS",
    "RESPONSE_KEY_LIMIT",
    "RESPONSE_KEY_NEXT_CURSOR",
    "RESPONSE_KEY_HAS_MORE",
    "RESPONSE_KEY_CACHED",
]
