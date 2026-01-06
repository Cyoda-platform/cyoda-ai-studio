"""Chat Service for conversation business logic.

This module provides a backward-compatible wrapper for the refactored service package.
All functionality has been split into focused modules within service/.
"""

# Re-export all public APIs from the package
from .service import (
    ChatService,
    CacheResult,
    PaginationResult,
    ChatCacheManager,
    CACHE_KEY_PREFIX,
    RESPONSE_KEY_CHATS,
    FIELD_TECHNICAL_ID,
)

__all__ = [
    "ChatService",
    "CacheResult",
    "PaginationResult",
    "ChatCacheManager",
    "CACHE_KEY_PREFIX",
    "RESPONSE_KEY_CHATS",
    "FIELD_TECHNICAL_ID",
]
