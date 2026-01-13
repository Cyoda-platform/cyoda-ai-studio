"""
Validation utilities for route handlers.

Provides decorators for automatic request validation using Pydantic models.
"""

import logging
from functools import wraps
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError
from quart import request

from application.routes.common.response import APIResponse

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def validate_json(model: Type[T]):
    """
    Decorator to validate JSON request body against Pydantic model.

    Automatically parses and validates the request body, making validated
    data available via request.validated_data attribute.

    Args:
        model: Pydantic model class for validation

    Returns:
        Decorated function with automatic validation

    Example:
        >>> @validate_json(GenerateTestTokenRequest)
        >>> async def create_token():
        >>>     data = request.validated_data
        >>>     # data is now a validated GenerateTestTokenRequest instance
        >>>     return APIResponse.success({"token": "..."})

    Validation errors are automatically returned as 400 Bad Request with
    detailed error messages.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Parse JSON body
                json_data = await request.get_json()

                if json_data is None:
                    return APIResponse.error(
                        "Request body required",
                        400,
                        details={"expected": "application/json"},
                    )

                # Validate against model
                validated = model(**json_data)

                # Store validated data on request object
                request.validated_data = validated

                # Call original function
                return await func(*args, **kwargs)

            except ValidationError as e:
                # Extract validation errors
                errors = []
                for error in e.errors():
                    field = " -> ".join(str(loc) for loc in error["loc"])
                    message = error["msg"]
                    errors.append(
                        {"field": field, "message": message, "type": error["type"]}
                    )

                logger.warning(f"Validation error in {func.__name__}: {errors}")

                return APIResponse.error(
                    "Validation failed", 400, details={"errors": errors}
                )

            except Exception as e:
                logger.exception(f"Error parsing request in {func.__name__}: {e}")
                return APIResponse.internal_error("Failed to parse request")

        return wrapper

    return decorator


def validate_query_params(model: Type[T]):
    """
    Decorator to validate query parameters against Pydantic model.

    Similar to validate_json but for URL query parameters.

    Args:
        model: Pydantic model class for validation

    Returns:
        Decorated function with automatic validation

    Example:
        >>> class SearchParams(BaseModel):
        >>>     limit: int = 10
        >>>     offset: int = 0
        >>>
        >>> @validate_query_params(SearchParams)
        >>> async def list_items():
        >>>     params = request.validated_params
        >>>     return APIResponse.success([])
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Get query parameters as dict
                query_dict = dict(request.args)

                # Validate against model
                validated = model(**query_dict)

                # Store validated params on request object
                request.validated_params = validated

                # Call original function
                return await func(*args, **kwargs)

            except ValidationError as e:
                # Extract validation errors
                errors = []
                for error in e.errors():
                    field = " -> ".join(str(loc) for loc in error["loc"])
                    message = error["msg"]
                    errors.append(
                        {"field": field, "message": message, "type": error["type"]}
                    )

                logger.warning(
                    f"Query parameter validation error in {func.__name__}: {errors}"
                )

                return APIResponse.error(
                    "Invalid query parameters", 400, details={"errors": errors}
                )

            except Exception as e:
                logger.exception(
                    f"Error parsing query parameters in {func.__name__}: {e}"
                )
                return APIResponse.internal_error("Failed to parse query parameters")

        return wrapper

    return decorator
