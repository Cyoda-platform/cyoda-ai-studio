"""
Chat Service for conversation business logic.

Encapsulates conversation-related business operations, separating them from HTTP concerns.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from application.entity.conversation import Conversation
from application.repositories.conversation_repository import ConversationRepository
from application.routes.common.constants import (
    CACHE_TTL_SECONDS,
    CHAT_LIST_DEFAULT_LIMIT,
)
from application.services.edge_message_persistence_service import (
    EdgeMessagePersistenceService,
)
from common.service.entity_service import SearchConditionRequest

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for chat/conversation business operations.

    Provides high-level conversation management with caching and validation.
    """

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        persistence_service: EdgeMessagePersistenceService,
    ):
        """
        Initialize chat service.

        Args:
            conversation_repository: Repository for conversation data access
            persistence_service: Service for edge message persistence
        """
        self.conversation_repo = conversation_repository
        self.persistence_service = persistence_service
        self._chat_list_cache: Dict[str, tuple[List[Dict], float]] = {}

    async def create_conversation(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        file_blob_ids: Optional[List[str]] = None,
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: Owner user ID
            name: Conversation name
            description: Conversation description (optional)
            file_blob_ids: List of file blob IDs attached (optional)

        Returns:
            Created conversation

        Example:
            >>> service = ChatService(repo, persistence)
            >>> conv = await service.create_conversation(
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

        created = await self.conversation_repo.create(conversation)
        logger.info(f"Created conversation {created.technical_id} for user {user_id}")

        # Invalidate cache
        self.invalidate_cache(user_id)

        return created

    async def get_conversation(self, technical_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            technical_id: Conversation technical ID

        Returns:
            Conversation or None if not found

        Example:
            >>> conv = await service.get_conversation("123-456")
        """
        return await self.conversation_repo.get_by_id(technical_id)

    async def update_conversation(self, conversation: Conversation) -> Conversation:
        """
        Update conversation with automatic retry on conflicts.

        Args:
            conversation: Conversation with updates

        Returns:
            Updated conversation

        Example:
            >>> conv.name = "Updated Name"
            >>> updated = await service.update_conversation(conv)
        """
        updated = await self.conversation_repo.update_with_retry(conversation)
        logger.info(f"Updated conversation {updated.technical_id}")

        # Invalidate cache
        self.invalidate_cache(updated.user_id)

        return updated

    async def delete_conversation(self, technical_id: str, user_id: str) -> None:
        """
        Delete conversation.

        Args:
            technical_id: Conversation technical ID
            user_id: User ID for cache invalidation

        Example:
            >>> await service.delete_conversation("123-456", "alice")
        """
        await self.conversation_repo.delete(technical_id)
        logger.info(f"Deleted conversation {technical_id}")

        # Invalidate cache
        self.invalidate_cache(user_id)

    async def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = CHAT_LIST_DEFAULT_LIMIT,
        before: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict:
        """
        List conversations with pagination and caching.

        Args:
            user_id: Filter by user ID (None for all conversations - superuser)
            limit: Maximum number of results
            before: ISO timestamp for cursor-based pagination
            use_cache: Whether to use cache (default True)

        Returns:
            Dictionary with chats, pagination info, and cache status

        Example:
            >>> result = await service.list_conversations(user_id="alice", limit=50)
            >>> print(result["chats"])
        """
        # Check cache
        cache_key = f"chats:{user_id or 'all'}"
        current_time = datetime.now(timezone.utc).timestamp()

        if use_cache and not before and limit == CHAT_LIST_DEFAULT_LIMIT:
            if cache_key in self._chat_list_cache:
                cached_chats, cache_time = self._chat_list_cache[cache_key]
                if current_time - cache_time < CACHE_TTL_SECONDS:
                    cache_age = current_time - cache_time
                    logger.info(
                        f"💾 CACHE HIT for {cache_key} (age: {cache_age:.1f}s, "
                        f"{len(cached_chats)} chats)"
                    )
                    return {
                        "chats": cached_chats[:limit],
                        "limit": limit,
                        "next_cursor": (
                            cached_chats[-1]["date"] if len(cached_chats) == limit else None
                        ),
                        "has_more": len(cached_chats) == limit,
                        "cached": True,
                    }

        # Fetch from repository
        response_list = await self.conversation_repo.search(
            user_id=user_id, limit=limit + 1, point_in_time=before
        )

        # Extract and format conversations
        user_chats = self._extract_conversations_from_response(response_list)

        # Sort by date descending
        user_chats.sort(key=lambda x: x.get("date", ""), reverse=True)

        # Determine pagination
        has_more = len(user_chats) > limit
        if has_more:
            user_chats = user_chats[:limit]

        next_cursor = user_chats[-1]["date"] if has_more and len(user_chats) > 0 else None

        # Update cache
        if use_cache and not before and limit == CHAT_LIST_DEFAULT_LIMIT and user_id:
            self._chat_list_cache[cache_key] = (user_chats, current_time)
            logger.info(f"💾 Cache updated for {cache_key} with {len(user_chats)} chats")

        return {
            "chats": user_chats,
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "cached": False,
        }

    def _extract_conversations_from_response(self, response_list: List) -> List[Dict]:
        """
        Extract conversation summaries from entity service response.

        Args:
            response_list: Raw response from entity service

        Returns:
            List of conversation dictionaries
        """
        user_chats = []
        for resp in response_list:
            if hasattr(resp, "data") and hasattr(resp, "metadata"):
                cyoda_response = resp.data
                tech_id = resp.metadata.id

                if isinstance(cyoda_response, dict) and "data" in cyoda_response:
                    entity_data = cyoda_response["data"]
                    name = entity_data.get("name", "")
                    description = entity_data.get("description", "")
                    date = entity_data.get("date", "") or entity_data.get("created_at", "")
                else:
                    name = ""
                    description = ""
                    date = ""

                user_chats.append(
                    {
                        "technical_id": tech_id,
                        "name": name,
                        "description": description,
                        "date": date,
                    }
                )
            elif isinstance(resp, dict):
                conv_data = resp.get("data", resp)
                tech_id = resp.get("technical_id", "") or conv_data.get("technical_id", "")

                user_chats.append(
                    {
                        "technical_id": tech_id,
                        "name": conv_data.get("name", ""),
                        "description": conv_data.get("description", ""),
                        "date": conv_data.get("date", "") or conv_data.get("created_at", ""),
                    }
                )

        return user_chats

    def validate_ownership(
        self, conversation: Conversation, user_id: str, is_superuser: bool = False
    ) -> None:
        """
        Validate that user has access to conversation.

        Args:
            conversation: Conversation to check
            user_id: Requesting user ID
            is_superuser: Whether user has superuser privileges

        Raises:
            PermissionError: If user doesn't have access

        Example:
            >>> service.validate_ownership(conv, "alice", False)
        """
        if is_superuser:
            return

        if conversation.user_id != user_id:
            raise PermissionError(
                f"User {user_id} does not have access to chat {conversation.technical_id}"
            )

    async def transfer_guest_chats(
        self, guest_user_id: str, authenticated_user_id: str
    ) -> int:
        """
        Transfer chats from guest user to authenticated user.

        Args:
            guest_user_id: Guest user ID (must start with 'guest.')
            authenticated_user_id: Authenticated user ID (must not start with 'guest.')

        Returns:
            Number of chats transferred

        Raises:
            ValueError: If user IDs are invalid

        Example:
            >>> count = await service.transfer_guest_chats("guest.123", "alice")
            >>> print(f"Transferred {count} chats")
        """
        # Validate user IDs
        if not guest_user_id.startswith("guest."):
            raise ValueError("Source user must be a guest user")
        if authenticated_user_id.startswith("guest."):
            raise ValueError("Cannot transfer chats to guest user")

        logger.info(f"🔄 Starting chat transfer from {guest_user_id} to {authenticated_user_id}")

        # Find all guest chats
        guest_chats = await self.conversation_repo.search(user_id=guest_user_id)

        transferred_count = 0
        for chat_response in guest_chats:
            if hasattr(chat_response, "metadata"):
                conversation = await self.conversation_repo.get_by_id(
                    chat_response.metadata.id
                )
                if conversation:
                    conversation.user_id = authenticated_user_id
                    await self.conversation_repo.update_with_retry(conversation)
                    transferred_count += 1
                    logger.debug(f"✅ Transferred chat {conversation.technical_id}")

        # Invalidate caches
        self.invalidate_cache(guest_user_id)
        self.invalidate_cache(authenticated_user_id)

        logger.info(
            f"✅ Chat transfer completed: {transferred_count} chats transferred "
            f"from {guest_user_id} to {authenticated_user_id}"
        )

        return transferred_count

    def invalidate_cache(self, user_id: str) -> None:
        """
        Invalidate chat list cache for user.

        Args:
            user_id: User ID to invalidate cache for

        Example:
            >>> service.invalidate_cache("alice")
        """
        cache_key = f"chats:{user_id}"
        if cache_key in self._chat_list_cache:
            del self._chat_list_cache[cache_key]
            logger.debug(f"Cache invalidated for {cache_key}")
