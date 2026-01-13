"""Cache management for chat service."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from common.constants import CACHE_TTL_SECONDS

from .constants import (
    CACHE_ALL_USERS,
    CACHE_KEY_PREFIX,
    CACHE_KEY_SEPARATOR,
    FIELD_DATE,
)
from .models import CacheResult

logger = logging.getLogger(__name__)


class ChatCacheManager:
    """Manages caching for chat lists."""

    def __init__(self):
        self._chat_list_cache: Dict[str, tuple[List[Dict], float]] = {}

    def build_cache_key(self, user_id: Optional[str]) -> str:
        """Build cache key from user ID.

        Args:
            user_id: User ID (None for all users)

        Returns:
            Cache key string
        """
        user_part = user_id if user_id else CACHE_ALL_USERS
        return f"{CACHE_KEY_PREFIX}{CACHE_KEY_SEPARATOR}{user_part}"

    def check_cache_validity(self, cache_time: float, current_time: float) -> bool:
        """Check if cache entry is still valid.

        Args:
            cache_time: Timestamp when cache was created
            current_time: Current timestamp

        Returns:
            True if cache is still valid
        """
        age = current_time - cache_time
        return age < CACHE_TTL_SECONDS

    def get_from_cache(
        self, cache_key: str, limit: int, current_time: float
    ) -> CacheResult:
        """Retrieve and validate cached chat list.

        Args:
            cache_key: Cache key to look up
            limit: Result limit
            current_time: Current timestamp

        Returns:
            CacheResult with hit status and chats
        """
        if cache_key not in self._chat_list_cache:
            return CacheResult(hit=False)

        cached_chats, cache_time = self._chat_list_cache[cache_key]

        if not self.check_cache_validity(cache_time, current_time):
            return CacheResult(hit=False)

        cache_age = current_time - cache_time
        logger.info(
            f"💾 CACHE HIT for {cache_key} (age: {cache_age:.1f}s, "
            f"{len(cached_chats)} chats)"
        )

        return CacheResult(hit=True, chats=cached_chats[:limit], cache_age=cache_age)

    def update_cache(
        self, cache_key: str, chats: List[Dict], current_time: float
    ) -> None:
        """Update cache with new data.

        Args:
            cache_key: Cache key to update
            chats: Chats to cache
            current_time: Current timestamp
        """
        self._chat_list_cache[cache_key] = (chats, current_time)
        logger.info(f"💾 Cache updated for {cache_key} with {len(chats)} chats")

    def invalidate_cache(self, user_id: str) -> None:
        """Invalidate chat list cache for user.

        Args:
            user_id: User ID to invalidate cache for

        Example:
            >>> manager.invalidate_cache("alice")
        """
        cache_key = self.build_cache_key(user_id)
        if cache_key in self._chat_list_cache:
            del self._chat_list_cache[cache_key]
            logger.debug(f"Cache invalidated for {cache_key}")
