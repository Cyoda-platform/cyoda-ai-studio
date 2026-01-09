"""
Authentication middleware for Quart routes.

Provides decorators for protecting routes with JWT authentication.
"""

import functools
import logging
from typing import Any, Callable

from quart import jsonify, request

from common.utils.jwt_utils import (
    TokenExpiredError,
    TokenValidationError,
    get_user_info_from_header,
)

logger = logging.getLogger(__name__)


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for a route.

    Validates the JWT token from the Authorization header and attaches
    user information to the request object:
    - request.user_id: The user ID from the token
    - request.is_superuser: Whether the user has superuser privileges
    - request.org_id: Organization ID (defaults to user_id.lower())

    If no Authorization header is provided or the token is invalid,
    returns a 401 Unauthorized response.

    Usage:
        @app.route('/protected')
        @require_auth
        async def protected_route():
            user_id = request.user_id
            return {'message': f'Hello {user_id}'}
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            logger.warning("Missing Authorization header")
            return jsonify({"error": "Unauthorized - missing token"}), 401

        try:
            user_id, is_superuser = get_user_info_from_header(auth_header)

            # Attach user info to request object
            request.user_id = user_id
            request.is_superuser = is_superuser
            request.org_id = user_id.lower()

            logger.debug(f"Authenticated user: {user_id}, superuser: {is_superuser}")

            return await func(*args, **kwargs)

        except TokenExpiredError:
            logger.warning("Token expired")
            return jsonify({"error": "Unauthorized - token expired"}), 401

        except TokenValidationError as e:
            logger.warning(f"Invalid token: {e}")
            return jsonify({"error": "Unauthorized - invalid token"}), 401

        except Exception as e:
            logger.exception(f"Authentication error: {e}")
            return jsonify({"error": "Unauthorized - authentication failed"}), 401

    return wrapper
