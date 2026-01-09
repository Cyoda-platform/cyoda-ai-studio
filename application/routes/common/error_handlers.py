"""
Centralized error handling middleware.

Provides consistent error handling across all routes with automatic
error logging and standardized response format.
"""

import logging
from typing import Callable

from pydantic import ValidationError
from quart import Quart, jsonify
from werkzeug.exceptions import HTTPException

from application.routes.common.response import APIResponse
from common.utils.jwt_utils import TokenExpiredError, TokenValidationError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Quart) -> None:
    """
    Register centralized error handlers for the application.

    Handles:
    - ValidationError (Pydantic) → 400 Bad Request
    - TokenExpiredError → 401 Unauthorized
    - TokenValidationError → 401 Unauthorized
    - PermissionError → 403 Forbidden
    - HTTPException (Werkzeug) → Appropriate status
    - Exception (Generic) → 500 Internal Server Error

    Args:
        app: Quart application instance

    Example:
        >>> from quart import Quart
        >>> app = Quart(__name__)
        >>> register_error_handlers(app)
    """

    @app.errorhandler(ValidationError)
    async def handle_validation_error(error: ValidationError):
        """
        Handle Pydantic validation errors.

        Returns 400 Bad Request with detailed validation errors.
        """
        # Extract validation errors
        errors = []
        for err in error.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            message = err["msg"]
            errors.append({"field": field, "message": message, "type": err["type"]})

        logger.warning(f"Validation error: {errors}")

        return APIResponse.error("Validation failed", 400, details={"errors": errors})

    @app.errorhandler(TokenExpiredError)
    async def handle_token_expired(error: TokenExpiredError):
        """
        Handle expired JWT tokens.

        Returns 401 Unauthorized.
        """
        logger.warning(f"Token expired: {error}")
        return APIResponse.unauthorized("Token has expired")

    @app.errorhandler(TokenValidationError)
    async def handle_token_invalid(error: TokenValidationError):
        """
        Handle invalid JWT tokens.

        Returns 401 Unauthorized.
        """
        logger.warning(f"Invalid token: {error}")
        return APIResponse.unauthorized("Invalid or malformed token")

    @app.errorhandler(PermissionError)
    async def handle_permission_error(error: PermissionError):
        """
        Handle permission/authorization errors.

        Returns 403 Forbidden.
        """
        logger.warning(f"Permission denied: {error}")
        return APIResponse.forbidden(str(error) or "Access denied")

    @app.errorhandler(ValueError)
    async def handle_value_error(error: ValueError):
        """
        Handle value errors (typically from business logic).

        Returns 400 Bad Request.
        """
        logger.warning(f"Value error: {error}")
        return APIResponse.error(str(error), 400)

    @app.errorhandler(HTTPException)
    async def handle_http_exception(error: HTTPException):
        """
        Handle Werkzeug HTTP exceptions.

        Preserves the original HTTP status code.
        """
        logger.info(f"HTTP exception: {error.code} - {error.description}")

        return (
            jsonify(
                {"error": error.name, "message": error.description, "status": "error"}
            ),
            error.code,
        )

    @app.errorhandler(404)
    async def handle_not_found(error):
        """
        Handle 404 Not Found errors.

        Returns standardized 404 response.
        """
        return APIResponse.not_found("Endpoint")

    @app.errorhandler(405)
    async def handle_method_not_allowed(error):
        """
        Handle 405 Method Not Allowed errors.

        Returns standardized 405 response.
        """
        return APIResponse.error("Method not allowed", 405)

    @app.errorhandler(Exception)
    async def handle_generic_exception(error: Exception):
        """
        Handle all uncaught exceptions.

        Returns 500 Internal Server Error.
        Logs full stack trace for debugging.
        """
        logger.exception(f"Unhandled exception: {error}")

        # In production, hide implementation details
        return APIResponse.internal_error("An unexpected error occurred")


def create_error_handler_wrapper(handler: Callable):
    """
    Create a wrapper that automatically handles errors in route handlers.

    Decorator that catches exceptions and converts them to appropriate
    API responses without needing try/except in every route.

    Args:
        handler: Route handler function

    Returns:
        Wrapped handler with error handling

    Example:
        >>> @create_error_handler_wrapper
        >>> async def my_route():
        >>>     # No try/except needed!
        >>>     result = do_something_that_might_fail()
        >>>     return APIResponse.success(result)
    """
    from functools import wraps

    @wraps(handler)
    async def wrapper(*args, **kwargs):
        try:
            return await handler(*args, **kwargs)
        except ValidationError as e:
            return await handle_validation_error(e)
        except TokenExpiredError as e:
            return await handle_token_expired(e)
        except TokenValidationError as e:
            return await handle_token_invalid(e)
        except PermissionError as e:
            return await handle_permission_error(e)
        except ValueError as e:
            return await handle_value_error(e)
        except HTTPException as e:
            return await handle_http_exception(e)
        except Exception as e:
            logger.exception(f"Error in {handler.__name__}: {e}")
            return APIResponse.internal_error("An unexpected error occurred")

    return wrapper


# Dummy functions for scope (replaced by actual handlers when registered)
async def handle_validation_error(error):
    """Placeholder for validation error handler."""
    errors = [
        {"field": str(loc), "message": err["msg"]}
        for err in error.errors()
        for loc in err["loc"]
    ]
    return APIResponse.error("Validation failed", 400, details={"errors": errors})


async def handle_token_expired(error):
    """Placeholder for token expired handler."""
    return APIResponse.unauthorized("Token has expired")


async def handle_token_invalid(error):
    """Placeholder for token invalid handler."""
    return APIResponse.unauthorized("Invalid token")


async def handle_permission_error(error):
    """Placeholder for permission error handler."""
    return APIResponse.forbidden(str(error))


async def handle_value_error(error):
    """Placeholder for value error handler."""
    return APIResponse.error(str(error), 400)


async def handle_http_exception(error):
    """Placeholder for HTTP exception handler."""
    return jsonify({"error": str(error)}), 500
