"""Decorators for API data fetcher tools."""

from __future__ import annotations

import functools
import logging
from typing import Callable

from ..formatters.api_formatters import format_api_error

logger = logging.getLogger(__name__)


def handle_api_errors(func: Callable) -> Callable:
    """Decorator to handle API errors.

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
            logger.exception(f"Failed in {func.__name__}: {e}")
            return format_api_error(str(e))

    return wrapper
