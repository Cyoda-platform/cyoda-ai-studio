"""
Authentication utilities for route handlers.

Centralizes JWT token validation and user information extraction.
"""

import logging
from typing import Tuple

from quart import request

from common.utils.jwt_utils import (
    TokenExpiredError,
    TokenValidationError,
    get_user_info_from_header,
)

logger = logging.getLogger(__name__)


async def get_authenticated_user() -> Tuple[str, bool]:
    """
    Extract user ID and superuser status from JWT token in Authorization header.

    Validates JWT tokens and extracts:
    - user_id from 'caas_org_id' claim
    - is_superuser from 'caas_cyoda_employee' claim

    Guest tokens (user_id starts with 'guest.') are signature-verified.
    Other tokens are decoded without verification (assumes external auth).

    Returns:
        tuple: (user_id, is_superuser)

    Raises:
        TokenExpiredError: If token has expired
        TokenValidationError: If token is invalid or malformed

    Example:
        >>> user_id, is_superuser = await get_authenticated_user()
        >>> print(f"User: {user_id}, Admin: {is_superuser}")
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header:
        # No auth header - return default guest session
        return "guest.anonymous", False

    try:
        user_id, is_superuser = get_user_info_from_header(auth_header)
        return user_id, is_superuser

    except TokenExpiredError:
        logger.warning("Token has expired")
        raise

    except TokenValidationError as e:
        logger.warning(f"Invalid token: {e}")
        raise
