"""Decorators for the Setup agent tools."""

from __future__ import annotations

import functools
import logging
from typing import Callable

from google.adk.tools.tool_context import ToolContext

from ..constants.constants import GUEST_USER_PREFIX, KEY_USER_ID
from ..formatters.common_formatters import format_error

logger = logging.getLogger(__name__)


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator to handle tool errors gracefully.

    Args:
        func: The async function to wrap

    Returns:
        Wrapped function that catches and logs exceptions
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error in {func.__name__}: {str(e)}"
            logger.exception(error_msg)
            return format_error(error_msg)

    return wrapper


def require_authenticated_user(func: Callable) -> Callable:
    """Decorator to ensure user is authenticated (not a guest).

    Args:
        func: The async function to wrap

    Returns:
        Wrapped function that checks authentication
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Find the ToolContext argument
        tool_context = None
        for arg in args:
            if isinstance(arg, ToolContext):
                tool_context = arg
                break

        if not tool_context:
            tool_context = kwargs.get("tool_context")

        if not tool_context:
            return format_error(
                f"Tool {func.__name__} requires ToolContext but none was provided"
            )

        user_id = tool_context.state.get(KEY_USER_ID, "guest.user")

        if user_id.startswith(GUEST_USER_PREFIX):
            return format_error(
                "This operation requires authentication. Please log in first."
            )

        return await func(*args, **kwargs)

    return wrapper
