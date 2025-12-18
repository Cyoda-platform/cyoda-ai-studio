"""
Rate limiting utilities for route handlers.

Provides standardized rate limit key functions.
"""

from quart import request


async def default_rate_limit_key() -> str:
    """
    Generate rate limit key based on client IP address.

    Used for anonymous/unauthenticated endpoints where user_id is not available.

    Returns:
        str: Client IP address or "unknown" if not available

    Example:
        >>> @rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
        >>> async def my_endpoint():
        >>>     pass
    """
    return request.remote_addr or "unknown"


async def user_rate_limit_key() -> str:
    """
    Generate rate limit key based on authenticated user ID.

    Used for authenticated endpoints where we want per-user rate limiting.
    Falls back to IP-based limiting if user_id is not available.

    Returns:
        str: User ID from request.user_id attribute, or IP address as fallback

    Example:
        >>> @require_auth
        >>> @rate_limit(50, timedelta(minutes=1), key_function=user_rate_limit_key)
        >>> async def my_protected_endpoint():
        >>>     pass
    """
    return getattr(request, "user_id", request.remote_addr or "anonymous")
