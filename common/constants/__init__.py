"""Service and business logic constants."""

# ============================================================================
# Chat Service Configuration
# ============================================================================

# Time-to-live for chat list cache (seconds)
CACHE_TTL_SECONDS = 30

# Default limit for paginated chat list requests
CHAT_LIST_DEFAULT_LIMIT = 100

# Maximum limit for paginated requests
CHAT_LIST_MAX_LIMIT = 1000

# ============================================================================
# Retry Configuration
# ============================================================================

# Maximum number of retry attempts for conversation updates
MAX_CONVERSATION_UPDATE_RETRIES = 5

# Base delay for exponential backoff retry logic (seconds)
RETRY_BASE_DELAY_SECONDS = 0.1

__all__ = [
    'CACHE_TTL_SECONDS',
    'CHAT_LIST_DEFAULT_LIMIT',
    'CHAT_LIST_MAX_LIMIT',
    'MAX_CONVERSATION_UPDATE_RETRIES',
    'RETRY_BASE_DELAY_SECONDS',
]
