"""Decorators for entity management tools."""

from __future__ import annotations

import functools
import logging
from typing import Callable

from ...common.formatters.entity_formatters import format_entity_error

logger = logging.getLogger(__name__)


def handle_entity_errors(func: Callable) -> Callable:
    """Decorator to handle entity tool errors gracefully.

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
            error_msg = str(e)
            logger.exception(f"Failed to {func.__name__}: {error_msg}")
            return format_entity_error(error_msg)

    return wrapper
