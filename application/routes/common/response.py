"""
Response utilities for standardized API responses.

Provides consistent response formatting across all routes.
"""

from typing import Any, Dict, Tuple

from quart import Response, jsonify


class APIResponse:
    """
    Standardized API response helper.

    Ensures consistent response format across all endpoints.
    """

    @staticmethod
    def success(data: Any, status: int = 200) -> Tuple[Response, int]:
        """
        Create a successful response.

        Args:
            data: Response data (dict, list, or serializable object)
            status: HTTP status code (default: 200)

        Returns:
            tuple: (Response object, status code)

        Example:
            >>> return APIResponse.success({"message": "OK"})
            >>> return APIResponse.success(user_list, 200)
        """
        return jsonify(data), status

    @staticmethod
    def error(
        message: str,
        status: int = 400,
        details: Any = None,
        error_code: str = None,
        modal: Dict[str, Any] = None,
    ) -> Tuple[Response, int]:
        """
        Create an error response.

        Args:
            message: Error message
            status: HTTP status code (default: 400)
            details: Additional error details (optional)
            error_code: Error code for client-side handling (optional)
            modal: Modal configuration for UI display (optional)

        Returns:
            tuple: (Response object, status code)

        Example:
            >>> return APIResponse.error("Invalid request", 400)
            >>> return APIResponse.error("Validation failed", 422, details=validation_errors)
            >>> return APIResponse.error("Limit exceeded", 403, error_code="LIMIT_EXCEEDED", modal={...})
        """
        error_data: Dict[str, Any] = {"error": message}
        if details is not None:
            error_data["details"] = details
        if error_code is not None:
            error_data["error_code"] = error_code
        if modal is not None:
            error_data["modal"] = modal
        return jsonify(error_data), status

    @staticmethod
    def not_found(resource: str = "Resource") -> Tuple[Response, int]:
        """
        Create a 404 Not Found response.

        Args:
            resource: Name of the resource that was not found

        Returns:
            tuple: (Response object, 404)

        Example:
            >>> return APIResponse.not_found("Chat")
            >>> return APIResponse.not_found("User")
        """
        return APIResponse.error(f"{resource} not found", 404)

    @staticmethod
    def forbidden(message: str = "Access denied") -> Tuple[Response, int]:
        """
        Create a 403 Forbidden response.

        Args:
            message: Custom forbidden message

        Returns:
            tuple: (Response object, 403)

        Example:
            >>> return APIResponse.forbidden()
            >>> return APIResponse.forbidden("Insufficient permissions")
        """
        return APIResponse.error(message, 403)

    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> Tuple[Response, int]:
        """
        Create a 401 Unauthorized response.

        Args:
            message: Custom unauthorized message

        Returns:
            tuple: (Response object, 401)

        Example:
            >>> return APIResponse.unauthorized()
            >>> return APIResponse.unauthorized("Token expired")
        """
        return APIResponse.error(message, 401)

    @staticmethod
    def internal_error(message: str = "Internal server error") -> Tuple[Response, int]:
        """
        Create a 500 Internal Server Error response.

        Args:
            message: Custom error message

        Returns:
            tuple: (Response object, 500)

        Example:
            >>> return APIResponse.internal_error()
            >>> return APIResponse.internal_error("Database connection failed")
        """
        return APIResponse.error(message, 500)
