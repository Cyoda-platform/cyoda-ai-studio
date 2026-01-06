"""
Constants used across route handlers.

Centralizes magic numbers and configuration values to improve maintainability.
"""

# Re-export common constants to maintain backward compatibility
from common.constants import (
    CACHE_TTL_SECONDS,
    CHAT_LIST_DEFAULT_LIMIT,
    CHAT_LIST_MAX_LIMIT,
    MAX_CONVERSATION_UPDATE_RETRIES,
    RETRY_BASE_DELAY_SECONDS,
)

# ============================================================================
# HTTP Timeout Configuration
# ============================================================================

# Default timeout for HTTP requests (seconds)
DEFAULT_HTTP_TIMEOUT_SECONDS = 30.0

# Timeout for long-running HTTP requests (seconds)
LONG_RUNNING_HTTP_TIMEOUT_SECONDS = 60.0

# Timeout for health check requests (seconds)
HEALTH_CHECK_TIMEOUT_SECONDS = 10.0

# ============================================================================
# Namespace Patterns
# ============================================================================

# Kubernetes namespace pattern for Cyoda environments
# Example: client-myorg-dev
NAMESPACE_PATTERN_ENVIRONMENT = "client-{org_id}-{env_name}"

# Kubernetes namespace pattern for user applications
# Example: client-1-myorg-dev-myapp
NAMESPACE_PATTERN_APPLICATION = "client-1-{org_id}-{env_name}-{app_name}"

# Kubernetes namespace pattern for Cyoda core
# Example: client-myorg
NAMESPACE_PATTERN_CORE = "client-{org_id}"

# ============================================================================
# Log Index Patterns
# ============================================================================

# Elasticsearch index pattern for environment logs
# Example: logs-client-myorg-dev*
LOG_INDEX_PATTERN_ENVIRONMENT = "logs-client-{org_namespace}-{env_namespace}*"

# Elasticsearch index pattern for application logs
# Example: logs-client-1-myorg-dev-myapp*
LOG_INDEX_PATTERN_APPLICATION = "logs-client-1-{org_namespace}-{env_namespace}-{app_namespace}*"

# ============================================================================
# Token Expiry Configuration
# ============================================================================

# Guest token expiry duration (weeks)
GUEST_TOKEN_EXPIRY_WEEKS = 50

# API key expiry duration (days)
API_KEY_EXPIRY_DAYS = 365

# Service account token expiry duration (seconds)
SERVICE_ACCOUNT_TOKEN_EXPIRY_SECONDS = 31536000  # 1 year

# ============================================================================
# Elasticsearch Configuration
# ============================================================================

# Maximum number of results returned by Elasticsearch queries
ELASTICSEARCH_MAX_SIZE = 10000

# Default page size for log search results
ELASTICSEARCH_DEFAULT_SIZE = 50

# ============================================================================
# SSE Streaming Configuration
# ============================================================================

# Interval between SSE heartbeat messages (seconds)
SSE_HEARTBEAT_INTERVAL_SECONDS = 15

# Interval between SSE event messages (seconds)
SSE_EVENT_INTERVAL_SECONDS = 30

# Default poll interval for task progress streaming (seconds)
TASK_PROGRESS_POLL_INTERVAL_SECONDS = 3

# ============================================================================
# Rate Limiting Defaults
# ============================================================================

# Default rate limit for standard endpoints (requests per minute)
RATE_LIMIT_STANDARD = 100

# Rate limit for token generation endpoints (requests per 5 minutes)
RATE_LIMIT_TOKEN_GENERATION = 5

# Rate limit for metrics query endpoints (requests per minute)
RATE_LIMIT_METRICS_QUERY = 600

# Rate limit for log search endpoints (requests per minute)
RATE_LIMIT_LOG_SEARCH = 30

# Rate limit for agent endpoints (requests per minute)
RATE_LIMIT_AGENT = 50
