"""Common utilities for environment agent tools.

This module provides reusable decorators, data classes, and helper functions
to eliminate code duplication and enforce software development best practices.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional

import httpx
from google.adk.tools.tool_context import ToolContext

from common.config.config import ADK_TEST_MODE

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes for Encapsulating Related Arguments
# ============================================================================


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""

    build_id: str
    namespace: str
    task_id: Optional[str] = None
    hook: Optional[dict[str, Any]] = None


# ============================================================================
# Decorators for Cross-Cutting Concerns
# ============================================================================


def require_authenticated_user(func: Callable) -> Callable:
    """Decorator that validates user is authenticated before executing tool.

    Checks if user_id starts with 'guest' and returns an error if so.
    This eliminates repetitive authentication checks across all tools.

    Can be bypassed for testing by setting ADK_TEST_MODE=true in .env

    Args:
        func: The tool function to wrap

    Returns:
        Wrapped function that validates authentication first
    """

    @wraps(func)
    async def wrapper(tool_context: ToolContext, *args, **kwargs):
        # Check if ADK test mode is enabled
        if ADK_TEST_MODE:
            logger.info(
                f"ADK_TEST_MODE=true: Skipping authentication check for {func.__name__}"
            )
            return await func(tool_context, *args, **kwargs)

        user_id = tool_context.state.get("user_id", "guest")

        if user_id.startswith("guest"):
            logger.warning(f"Tool {func.__name__} rejected for guest user: {user_id}")

            # Determine response format based on function signature or docstring
            # Most tools return JSON, some return plain strings
            error_message = "User is not logged in. Please sign up or log in first."

            # If function name suggests it returns JSON or has json in docstring
            if "json" in func.__doc__.lower() if func.__doc__ else False:
                return json.dumps({"error": error_message})

            return f"Error: {error_message}"

        return await func(tool_context, *args, **kwargs)

    return wrapper


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator that handles common exceptions for environment tools.

    Catches and formats HTTPStatusError and generic exceptions consistently.
    This eliminates repetitive try/except blocks across all tools.

    Args:
        func: The tool function to wrap

    Returns:
        Wrapped function with standardized error handling
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)

        except httpx.HTTPStatusError as e:
            error_msg = f"{func.__name__} failed with status {e.response.status_code}"
            logger.error(f"{error_msg}: {e.response.text}")

            # Determine if this is a 404 (common case)
            if e.response.status_code == 404:
                resource_name = kwargs.get(
                    "env_name", kwargs.get("app_name", "resource")
                )
                return json.dumps({"error": f"Resource '{resource_name}' not found."})

            return json.dumps({"error": error_msg})

        except Exception as e:
            error_msg = f"Error in {func.__name__}: {str(e)}"
            logger.exception(error_msg)
            return json.dumps({"error": error_msg})

    return wrapper


# ============================================================================
# Helper Functions for Common Operations
# ============================================================================


def construct_environment_url(namespace: str) -> str:
    """Construct environment URL from namespace.

    Args:
        namespace: The environment namespace

    Returns:
        Full environment URL
    """
    client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
    return f"https://{namespace}.{client_host}"


def validate_required_params(**params) -> Optional[str]:
    """Validate that required parameters are provided.

    Args:
        **params: Named parameters to validate (param_name=param_value)

    Returns:
        Error message if validation fails, None if all params valid
    """
    for param_name, param_value in params.items():
        if not param_value:
            return f"Error: {param_name} parameter is required but was not provided."
    return None


def format_error_response(error_message: str, as_json: bool = True) -> str:
    """Format error message consistently.

    Args:
        error_message: The error message
        as_json: Whether to return as JSON string

    Returns:
        Formatted error response
    """
    if as_json:
        return json.dumps({"error": error_message})
    return f"Error: {error_message}"


# ============================================================================
# Service Getters (Module-level instead of in functions)
# ============================================================================


def get_task_service():
    """Get task service instance.

    Returns:
        Task service instance
    """
    from services.services import get_task_service as _get_task_service

    return _get_task_service()


def get_deployment_status_tool():
    """Get deployment status tool function.

    Returns:
        get_deployment_status function
    """
    from application.agents.environment.tools import get_deployment_status

    return get_deployment_status
