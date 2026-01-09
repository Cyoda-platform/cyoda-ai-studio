"""List conversations with pagination and caching."""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from application.repositories.conversation_repository import ConversationRepository
from common.constants import CHAT_LIST_DEFAULT_LIMIT

from .cache import ChatCacheManager
from .constants import FIELD_DATE
from .formatters import (
    calculate_pagination,
    extract_conversations_from_response,
    format_response,
)
from .models import PaginationResult

logger = logging.getLogger(__name__)


async def list_conversations(
    conversation_repo: ConversationRepository,
    cache_manager: ChatCacheManager,
    user_id: Optional[str] = None,
    limit: int = CHAT_LIST_DEFAULT_LIMIT,
    before: Optional[str] = None,
    use_cache: bool = True,
) -> Dict:
    """List conversations with pagination and caching.

    Args:
        conversation_repo: Repository for conversation data access
        cache_manager: Cache manager
        user_id: Filter by user ID (None for all conversations - superuser)
        limit: Maximum number of results
        before: ISO timestamp for cursor-based pagination
        use_cache: Whether to use cache (default True)

    Returns:
        Dictionary with chats, pagination info, and cache status

    Example:
        >>> result = await list_conversations(repo, cache, user_id="alice", limit=50)
        >>> print(result["chats"])
    """
    # Step 1: Build cache key and check cache
    cache_key = cache_manager.build_cache_key(user_id)
    current_time = datetime.now(timezone.utc).timestamp()
    should_use_cache = use_cache and not before and limit == CHAT_LIST_DEFAULT_LIMIT

    # Step 2: Return cached data if valid
    if should_use_cache:
        cache_result = cache_manager.get_from_cache(cache_key, limit, current_time)
        if cache_result.hit:
            pagination = PaginationResult(
                has_more=len(cache_result.chats) == limit,
                next_cursor=(
                    cache_result.chats[-1][FIELD_DATE] if cache_result.chats else None
                ),
            )
            return format_response(cache_result.chats, pagination, cached=True)

    # Step 3: Fetch from repository
    response_list = await conversation_repo.search(
        user_id=user_id, limit=limit + 1, point_in_time=before
    )

    # Step 4: Extract and format conversations
    user_chats = extract_conversations_from_response(response_list)
    user_chats.sort(key=lambda x: x.get(FIELD_DATE, ""), reverse=True)

    # Step 5: Calculate pagination
    pagination = calculate_pagination(user_chats, limit)
    user_chats = user_chats[:limit]

    # Step 6: Update cache if appropriate
    should_cache = should_use_cache and user_id
    if should_cache:
        cache_manager.update_cache(cache_key, user_chats, current_time)

    # Step 7: Format and return response
    return format_response(user_chats, pagination, cached=False)
